#!/usr/bin/env python3
"""Ingest web articles into a brain's `raw/` (spec.md §6, web-article arm).

    python3 ingest_web.py <url> [<url> ...] --into <brain-dir> [--delay 1.5] [--json]

trafilatura does the extraction — benchmark leader, heuristic, local, no model
to download — and is imported inside this arm rather than at the top of the kit.
Everything else here is stdlib, so a member who never ingests a web page never
installs anything, and a machine without the library gets a named record saying
which line to run instead of a traceback.

The failure this arm exists to prevent is the quiet one. A paywalled page
returns HTTP 200 and a fluent 200-word teaser; extracted and distilled without
comment, it becomes a confident wiki page built on marketing copy, and nothing
downstream can tell. So an extraction that reads as a wall is **quarantined**:
kept outside `raw/` where the member can look at it, named in `log.md`, and
never distilled.

Everything the arm does is a `Record`; nothing raises and nothing is skipped in
silence. Exit 1 only when the whole corpus produced nothing.

Stdlib only, plus trafilatura where a page is actually being read.
"""
import json
import os
import sys

import cli
import rights
from fetching import DEFAULT_DELAY, FetchError, Fetcher
from raw_store import Manifest, RawStore, Record, log_manifest

SOURCE_FORMAT = "web"

#: Named on the record when the library is not installed, so the member sees the
#: one line that fixes it rather than an import error.
INSTALL_HINT = "pip install trafilatura"


def ingest(urls, brain, fetcher=None, extractor=None, delay=DEFAULT_DELAY):
    """Ingest `urls` into `brain`'s `raw/`. Never raises; returns a `Manifest`."""
    fetcher = fetcher or Fetcher(delay=delay)
    extractor = extractor or extract
    store = RawStore(brain)
    manifest = Manifest(store.brain)
    for url in urls:
        _ingest_one(url, store, manifest, fetcher, extractor)
    log_manifest(store.brain, manifest, "web")
    return manifest


def _ingest_one(url, store, manifest, fetcher, extractor):
    refusal = rights.refusal_for_url(url)
    if refusal:                             # refused before a single request goes out
        return manifest.add(Record(url, "failed", source_format=SOURCE_FORMAT,
                                   reason=refusal))
    try:
        response = fetcher(url)
    except FetchError as failure:
        return manifest.add(Record(url, "failed", source_format=SOURCE_FORMAT,
                                   reason=str(failure)))

    try:
        text, meta = extractor(response.text, url)
    except ImportError:
        return manifest.add(Record(url, "failed", source_format=SOURCE_FORMAT,
                                   reason="trafilatura is not installed — {}"
                                          .format(INSTALL_HINT)))
    except Exception as failure:            # one unreadable page never stops a corpus
        return manifest.add(Record(url, "failed", source_format=SOURCE_FORMAT,
                                   reason="could not extract the article: {}".format(failure)))

    meta = meta or {}
    if not (text or "").strip():
        return manifest.add(Record(url, "empty", source_format=SOURCE_FORMAT,
                                   reason="nothing readable was extracted from the page"))

    walled = rights.paywall_reason(text, url)
    if walled:
        parked = store.quarantine(text, meta.get("title") or url, url, walled)
        return manifest.add(Record(url, "failed", source_format=SOURCE_FORMAT,
                                   reason="{} — kept at {}".format(walled, parked)))

    already = store.duplicate_of(text)
    if already:
        return manifest.add(Record(url, "duplicate", source_format=SOURCE_FORMAT,
                                   reason="same text as {}".format(already)))

    raw = store.add(text, meta.get("title") or url, source=url,
                    source_format=SOURCE_FORMAT, title=meta.get("title"),
                    author=meta.get("author"), published=meta.get("date"))
    return manifest.add(Record(url, "ok", raw=raw, words=len(text.split()),
                               source_format=SOURCE_FORMAT))


def extract(html, url=""):
    """The article inside a page, as `(text, metadata)`. Imports trafilatura lazily."""
    import trafilatura                      # noqa: E402 — optional, per-arm dependency

    text = trafilatura.extract(html, url=url or None, include_comments=False,
                               include_tables=True, favor_precision=True) or ""
    meta = {}
    try:
        document = trafilatura.extract_metadata(html, default_url=url or None)
        if document is not None:
            meta = {"title": document.title, "author": document.author,
                    "date": document.date}
    except Exception:                       # metadata is a nicety; the text is the point
        meta = {}
    return text, meta


# --- cli -------------------------------------------------------------------

USAGE = ("usage: ingest_web.py <url> [<url> ...] --into <brain-dir> "
         "[--delay <seconds>] [--json]\n")


def main(argv):
    try:
        urls, options = cli.scan(argv, options={"--into": None, "--delay": DEFAULT_DELAY,
                                                "--json": False},
                                 flags=("--json",))
        delay = float(options["--delay"])
    except (cli.UsageError, ValueError) as failure:
        sys.stderr.write("ingest_web.py: {}\n{}".format(failure, USAGE))
        return 2

    if not urls or not options["--into"]:
        sys.stderr.write(USAGE)
        return 2

    manifest = ingest(urls, options["--into"], delay=delay)
    print(json.dumps(manifest.as_dict(), indent=2)
          if options["--json"] else manifest.summary())
    if manifest.whole_corpus_failed:
        sys.stderr.write("ingest_web.py: no article could be read — stop and talk to "
                         "the member rather than building an empty brain\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
