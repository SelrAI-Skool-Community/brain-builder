#!/usr/bin/env python3
"""Ingest PDFs and EPUBs into a brain's `raw/` (spec.md §6, documents arm).

    python3 ingest_docs.py <path> [<path> ...] --into <brain-dir> [--json]

PyMuPDF4LLM reads PDFs and EbookLib reads EPUBs. Both are imported inside the
reader that needs them, so a member who only ever ingests markdown installs
nothing, and a machine missing one gets a record naming the single line that
fixes it rather than a traceback halfway through a build.

Two failures here are worth more than the happy path.

**DRM is refused unopened.** Kindle, Audible and encrypted EPUB/PDF files are
turned away by `rights.py` before a reader touches them — circumventing DRM is a
separate offence with no personal-use safe harbour (docs/rights.md), so the kit
does not try, and does not suggest a way around it.

**A scanned PDF has no text layer**, and a reader run over one returns an empty
string rather than an error. Distilled silently, that is a book the brain
believes it has read. It comes out as `empty`, in the log, with OCR named as the
opt-in it is — the kit does not quietly acquire a model to read a picture.

Everything is a `Record`; nothing raises. Exit 1 only when the whole corpus
produced nothing.

Stdlib only, plus the reader for the format actually being read.
"""
import os
import sys
from html.parser import HTMLParser

import cli
import ingest_local
import rights
from raw_store import (Manifest, RawStore, Record, log_manifest, missing_reason,
                       report, walk_sources)

#: What this arm reads. Everything else is another arm's job or nobody's.
SUPPORTED = {".pdf": "pdf", ".epub": "epub"}

#: The one line that fixes a missing reader, per format.
INSTALL_HINTS = {"pdf": "pip install pymupdf4llm", "epub": "pip install EbookLib"}

_BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6",
               "section", "article", "blockquote", "tr", "table", "pre"}


def ingest(paths, brain, readers=None):
    """Ingest documents under `paths` into `brain`'s `raw/`. Never raises."""
    readers = readers or {"pdf": read_pdf, "epub": read_epub}
    store = RawStore(brain)
    manifest = Manifest(store.brain)
    for path, relpath in walk_sources(paths):
        _ingest_one(path, relpath, store, manifest, readers)
    log_manifest(store.brain, manifest, "docs")
    return manifest


def _ingest_one(path, relpath, store, manifest, readers):
    if relpath is None:                     # nothing at that path — never dropped
        return manifest.add(Record(path, "failed", reason=missing_reason(path)))

    refusal = rights.refusal_for_file(path)
    if refusal:                             # refused before any reader opens it
        return manifest.add(Record(path, "failed", reason=refusal))

    source_format = SUPPORTED.get(os.path.splitext(path)[1].lower())
    if source_format is None:
        return manifest.add(Record(path, "unsupported", reason=_no_reader(path)))

    try:
        text, meta = readers[source_format](path)
    except ImportError as failure:
        return manifest.add(Record(path, "failed", source_format=source_format,
                                   reason="{} — {}".format(
                                       failure, INSTALL_HINTS[source_format])))
    except Exception as failure:            # one bad document never stops a corpus
        return manifest.add(Record(path, "failed", source_format=source_format,
                                   reason=str(failure)))

    meta = meta or {}
    if not (text or "").strip():
        return manifest.add(Record(path, "empty", source_format=source_format,
                                   reason=_no_text(source_format)))

    already = store.duplicate_of(text)
    if already:
        return manifest.add(Record(path, "duplicate", source_format=source_format,
                                   reason="same text as {}".format(already)))

    return store.land(manifest, text,
                      meta.get("title") or os.path.splitext(os.path.basename(path))[0],
                      path, source_format, title=meta.get("title"),
                      author=meta.get("author"), published=meta.get("date"))


def read_pdf(path):
    """A PDF as markdown, with whatever the file says about itself."""
    import pymupdf4llm                      # noqa: E402 — optional, per-arm dependency

    text = pymupdf4llm.to_markdown(path) or ""
    return text, _pdf_metadata(path)


def _pdf_metadata(path):
    """Title and author off the PDF's own dictionary, if PyMuPDF is importable.

    A missing title is not worth failing a document over — the filename is a
    perfectly good name for the page, and the source path is the attribution.
    """
    try:
        import pymupdf                      # noqa: E402 — ships with pymupdf4llm
    except ImportError:
        try:
            import fitz as pymupdf          # noqa: E402 — its older import name
        except ImportError:
            return {}
    try:
        with pymupdf.open(path) as document:
            info = document.metadata or {}
    except Exception:
        return {}
    return {"title": info.get("title"), "author": info.get("author")}


def read_epub(path):
    """An EPUB's chapters as prose, in spine order, with its declared metadata."""
    import ebooklib                         # noqa: E402 — optional, per-arm dependency
    from ebooklib import epub               # noqa: E402

    book = epub.read_epub(path)
    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        chapter = html_to_text(item.get_content().decode("utf-8", "replace"))
        if chapter.strip():
            chapters.append(chapter.strip())
    return "\n\n".join(chapters), {"title": _dc(book, "title"),
                                   "author": _dc(book, "creator"),
                                   "date": _dc(book, "date")}


def _dc(book, field):
    try:
        entries = book.get_metadata("DC", field)
    except Exception:
        return None
    return entries[0][0] if entries else None


class _Prose(HTMLParser):
    """XHTML in, readable text out, paragraph breaks preserved."""

    SKIP = ("script", "style", "head")

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.chunks = []
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipping += 1
        elif tag in _BLOCK_TAGS:
            self.chunks.append("\n\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skipping:
            self.skipping -= 1
        elif tag in _BLOCK_TAGS:
            self.chunks.append("\n\n")

    def handle_data(self, data):
        if not self.skipping and data.strip():
            self.chunks.append(" ".join(data.split()))


def html_to_text(html):
    """The prose inside an EPUB chapter, blocks kept apart, markup gone."""
    parser = _Prose()
    parser.feed(html or "")
    parser.close()
    text = "".join(parser.chunks)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return "\n".join(line.strip() for line in text.strip().split("\n"))


def _no_reader(path):
    extension = os.path.splitext(path)[1].lower()
    if extension in ingest_local.SUPPORTED:
        return "ingest_local.py reads this file type, not this arm"
    return "no reader for this file type — this arm reads .pdf and .epub"


def _no_text(source_format):
    if source_format == "pdf":
        return ("no text layer — this looks like a scanned PDF. OCR is opt-in and "
                "not shipped in v1, so this document is not in the brain")
    return "no text in the file"


# --- cli -------------------------------------------------------------------

USAGE = "usage: ingest_docs.py <path> [<path> ...] --into <brain-dir> [--json]\n"


def main(argv):
    try:
        paths, options = cli.scan(argv, options={"--into": None, "--json": False},
                                  flags=("--json",))
    except cli.UsageError as failure:
        sys.stderr.write("ingest_docs.py: {}\n{}".format(failure, USAGE))
        return 2

    if not paths or not options["--into"]:
        sys.stderr.write(USAGE)
        return 2

    return report(ingest(paths, options["--into"]), "ingest_docs.py",
                  "no document could be read", as_json=options["--json"])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
