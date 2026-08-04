#!/usr/bin/env python3
"""What every ingestion arm shares: the manifest it returns, and the `raw/` it writes.

There are five arms now (local files, docs, YouTube, web, podcasts) and one set
of rules they all answer to (spec.md §6):

  every chunk is attributed   a `raw/` page carries where it came from and when
                              it was ingested — that is the rights stance made
                              mechanical, not a paragraph in a doc.
  `raw/` is immutable         a second run adds; it never overwrites. What is
                              already on disk is read back, so re-running after
                              a Gate 1 edit cannot clobber a page.
  nothing disappears quietly  every source becomes a `Record` with an outcome,
                              and everything that did not land is written to the
                              brain's `log.md`.

Keeping that here rather than in each arm is what stops five copies of the
provenance header drifting apart — the header *is* the attribution, and an arm
that quietly wrote a thinner one would break the stance without failing a test.

Stdlib only.
"""
import datetime
import hashlib
import json
import os
import re
import sys

import rights
from brain_contract import parse_frontmatter
from scaffold import derive_slug, log_event

#: Provenance keys, in the order a reader would want to meet them. Anything an
#: arm passes that is not here still lands, after these.
PROVENANCE_ORDER = ("source", "source_format", "title", "author", "published",
                    "duration", "transcript", "url")


class Record(object):
    """One source and what became of it."""

    def __init__(self, source, outcome, raw=None, words=0, source_format=None, reason=""):
        self.source = source
        self.outcome = outcome
        self.raw = raw
        self.words = words
        self.source_format = source_format
        self.reason = reason

    def as_dict(self):
        return {"source": self.source, "outcome": self.outcome, "raw": self.raw,
                "words": self.words, "format": self.source_format, "reason": self.reason}


class Manifest(object):
    """The whole run: what landed, what did not, and the line to narrate."""

    #: Everything that can become of a source. `ok` is the one that lands.
    OUTCOMES = ("ok", "empty", "duplicate", "unsupported", "failed")

    def __init__(self, brain):
        self.brain = brain
        self.records = []

    def add(self, record):
        self.records.append(record)
        return record

    def of(self, outcome):
        """Every record with `outcome` — see `OUTCOMES` for the five."""
        return [record for record in self.records if record.outcome == outcome]

    @property
    def ok(self):
        return self.of("ok")

    @property
    def empty(self):
        return self.of("empty")

    @property
    def duplicate(self):
        return self.of("duplicate")

    @property
    def unsupported(self):
        return self.of("unsupported")

    @property
    def failed(self):
        return self.of("failed")

    @property
    def words(self):
        return sum(record.words for record in self.ok)

    @property
    def counts(self):
        counts = {outcome: len(self.of(outcome)) for outcome in self.OUTCOMES}
        counts["words"] = self.words
        return counts

    @property
    def whole_corpus_failed(self):
        """Sources were found and none of their text is in the brain.

        The only condition that stops a build. Unsupported sources count towards
        it: a folder this arm cannot read is still a corpus that produced
        nothing, and the honest answer is to stop and say which arm it needs.
        Duplicates do not — their text is already in `raw/`, which is the whole
        point of re-running after a Gate 1 edit.
        """
        return bool(self.records) and not self.ok and not self.duplicate

    def summary(self):
        """The one line the build narrates, and the one line the log keeps."""
        parts = ["{} sources ingested ({:,} words)".format(len(self.ok), self.words)]
        for outcome in self.OUTCOMES[1:]:
            found = self.of(outcome)
            if found:
                parts.append("{} {}".format(len(found), outcome))
        return ", ".join(parts)

    def as_dict(self):
        return {"brain": self.brain, "counts": self.counts,
                "summary": self.summary(),
                "records": [record.as_dict() for record in self.records]}


class RawStore(object):
    """A brain's `raw/`: what is already in it, and how new material lands.

    Built once per run and then asked, rather than re-reading the directory per
    source: the dedup set and the taken names are both state that only this run
    changes.
    """

    def __init__(self, brain):
        self.brain = os.path.abspath(os.path.expanduser(brain))
        self.raw_dir = os.path.join(self.brain, "raw")
        os.makedirs(self.raw_dir, exist_ok=True)
        self.used_names, self.seen_text = self._read_back()

    def _read_back(self):
        """What a previous run left: the names taken and the text already held.

        Read off disk rather than assumed, because `raw/` is immutable (spec.md
        §2) and a re-run must not be able to overwrite a page a first run wrote.
        """
        used_names, seen_text = set(), {}
        for name in sorted(os.listdir(self.raw_dir)):
            if not name.endswith(".md"):
                continue
            used_names.add(name)
            with open(os.path.join(self.raw_dir, name), "r", encoding="utf-8") as handle:
                front, body, _ = parse_frontmatter(handle.read())
            seen_text[digest(body)] = front.get("source") or "raw/" + name
        return used_names, seen_text

    def duplicate_of(self, text):
        """The source this exact text already came from, or `None`."""
        return self.seen_text.get(digest(text))

    def add(self, text, name_hint, source, source_format, **provenance):
        """Write one attributed page and return its brain-relative path.

        Raises `rights.RightsError` on material with nothing to attribute it to.
        Arms land pages through `land()` rather than calling this directly, so
        that refusal becomes a record instead of an exception.
        """
        rights.require_attribution(dict(provenance, source=source,
                                        source_format=source_format))
        self.seen_text[digest(text)] = source
        name = self.name_for(name_hint)
        page = render_page(text, source=source, source_format=source_format, **provenance)
        with open(os.path.join(self.raw_dir, name), "w", encoding="utf-8") as handle:
            handle.write(page)
        return "raw/" + name

    def land(self, manifest, text, name_hint, source, source_format, **provenance):
        """Write the page and record it — or record why it could not be written.

        Every arm ends here, which is what keeps their promise identical: a
        source either becomes an `ok` record with a `raw/` path, or a `failed`
        one with the reason. Neither raises, because a network source with no
        title, no page and no enclosure is a thing the real world produces, and
        one of them must not take a build down.
        """
        try:
            raw = self.add(text, name_hint, source, source_format, **provenance)
        except (rights.RightsError, OSError) as failure:
            return manifest.add(Record(source or name_hint, "failed",
                                       source_format=source_format, reason=str(failure)))
        return manifest.add(Record(source, "ok", raw=raw, words=len(text.split()),
                                   source_format=source_format))

    def quarantine(self, text, name_hint, source, reason):
        """Park material the rights stance will not ingest, and say where.

        Quarantine is not deletion: a paywalled stub is kept where the member
        can look at it and decide, outside `raw/` so that nothing distilled into
        the wiki can ever have come from it. `quarantine/` is not part of the
        brain contract, which is exactly why lint walks past it.
        """
        directory = os.path.join(self.brain, "quarantine")
        os.makedirs(directory, exist_ok=True)
        name = _unique(derive_slug(name_hint) or "source", set(os.listdir(directory)))
        with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
            handle.write(render_page(text, source=source, source_format="quarantined",
                                     quarantined=reason))
        return "quarantine/" + name

    def name_for(self, hint):
        """The `raw/` filename for a source, kept unique across the whole corpus."""
        name = _unique(derive_slug(hint) or "source", self.used_names)
        self.used_names.add(name)
        return name


def digest(text):
    """A source's identity for exact-dedup purposes: its text, whitespace aside."""
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()


def render_page(text, **provenance):
    """One `raw/` page: the provenance header every chunk carries, then the text."""
    fields = [("type", "source")]
    keys = [key for key in PROVENANCE_ORDER if provenance.get(key)]
    keys += sorted(key for key in provenance
                   if key not in PROVENANCE_ORDER and provenance.get(key))
    fields += [(key, _one_line(provenance[key])) for key in keys]
    fields.append(("ingested", datetime.date.today().isoformat()))
    header = "".join("{}: {}\n".format(key, value) for key, value in fields)
    return "---\n{}---\n\n{}\n".format(header, text.strip())


def log_manifest(brain, manifest, label="ingest"):
    """Write the run's counts and every non-landing source into `log.md`.

    A brain with no `log.md` is not an error — the file is optional in the
    contract, and an arm pointed at a bare directory still has to run.
    """
    if not os.path.isfile(os.path.join(brain, "log.md")):
        return
    log_event(brain, "{}: {}".format(label, manifest.summary()))
    for record in manifest.records:
        if record.outcome in ("ok", "duplicate"):
            continue
        log_event(brain, "{} {}: {} — {}".format(
            label, record.outcome, record.source, record.reason))


def walk_sources(paths):
    """Every candidate file under `paths`, with the name it would be filed as.

    Shared by the two arms that take paths rather than URLs: what counts as a
    candidate is the same question for a folder of notes and a folder of books,
    and only the extension decides which arm can read it. Hidden files and
    Office lock files (`~$…`) are never candidates.

    A path that yields **nothing** — it does not exist, or it is a folder with
    no candidate files in it — comes back as `(path, None)` rather than being
    dropped. Ingestion fails loudly (spec.md §6): a mistyped or moved path the
    member approved at Gate 1 has to become a record and a `log.md` line, not a
    source that quietly was never there. Arms turn it into a `failed` record
    with `missing_reason(path)`.
    """
    found = []
    for source in paths:
        source = os.path.abspath(os.path.expanduser(source))
        if os.path.isfile(source):
            found.append((source, os.path.basename(source)))
            continue
        before = len(found)
        for dirpath, dirnames, filenames in os.walk(source):
            dirnames[:] = sorted(name for name in dirnames if not name.startswith("."))
            for filename in sorted(filenames):
                if filename.startswith(".") or filename.startswith("~$"):
                    continue
                path = os.path.join(dirpath, filename)
                found.append((path, os.path.relpath(path, source)))
        if len(found) == before:
            found.append((source, None))
    return found


def missing_reason(path):
    """Why a source path produced no candidate file at all."""
    if not os.path.exists(path):
        return "no such file or folder — nothing at this path to ingest"
    return "the folder holds no files to ingest"


def report(manifest, script, nothing, as_json=False, stdout=None, stderr=None):
    """Print an arm's manifest the one way every arm prints it, and exit-code it.

    The five arms had five copies of this, which is five chances for one of them
    to exit 0 on a corpus that produced nothing — the single condition that is
    supposed to stop a build.
    """
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    stdout.write((json.dumps(manifest.as_dict(), indent=2)
                  if as_json else manifest.summary()) + "\n")
    if manifest.whole_corpus_failed:
        stderr.write("{}: {} — stop and talk to the member rather than building "
                     "an empty brain\n".format(script, nothing))
        return 1
    return 0


def _unique(stem, taken):
    name, suffix = stem + ".md", 2
    while name in taken:
        name, suffix = "{}-{}.md".format(stem, suffix), suffix + 1
    return name


def _one_line(value):
    """Frontmatter values are one line — a title with a newline in it is not."""
    return re.sub(r"\s+", " ", str(value)).strip()
