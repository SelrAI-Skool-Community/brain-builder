#!/usr/bin/env python3
"""Ingest local files into a brain's `raw/` (spec.md §6, local-files arm).

    python3 ingest_local.py <path> [<path> ...] --into <brain-dir> [--json]

Handles md/txt/csv/json/docx. Every ingested file becomes one attributed page
under `raw/`: the source path and the ingest date ride with the text, because
the rights stance is that every chunk in a brain says where it came from.

Failure is a record, not an exception. A file that cannot be read, or that holds
no text at all, is counted and logged to the brain's `log.md`, and the run
carries on — one dead file has never been a reason to abandon a corpus. The one
exception is a corpus that yielded *nothing*, which exits non-zero so the build
stops rather than producing an empty brain. A folder of file types this arm
cannot read counts as exactly that: pointing the builder at a folder of PDFs is
the likeliest way to reach it, and `ingest_docs.py` is the arm it needs.

Dedup here is **exact**: identical text, whitespace-normalised. Near-verbatim
dedup (spec.md §6) is a corpus-wide question — a compilation restating three
other sources — and belongs to `dedup_corpus.py`, which sees the whole of
`raw/` at once rather than one file at a time.

The manifest, the provenance header and the immutable `raw/` are shared with
every other arm and live in `raw_store.py`.

Stdlib only: `.docx` is a zip of XML, which `zipfile` and `ElementTree` read
without a third-party library.
"""
import csv
import io
import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ElementTree

import cli
from raw_store import Manifest, RawStore, Record, log_manifest

TEXT_FORMATS = {".md": "md", ".markdown": "md", ".txt": "txt", ".text": "txt"}
SUPPORTED = dict(TEXT_FORMATS, **{".csv": "csv", ".json": "json", ".docx": "docx"})

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def ingest(sources, brain):
    """Ingest `sources` (files or folders) into `brain`'s `raw/`. Never raises.

    Returns a `Manifest`. Anything that failed is on it and in the brain's
    `log.md`, so the build can narrate counts and move on. Re-running against a
    brain that already holds material adds to it — `raw/` is immutable, and
    nothing already ingested is rewritten.
    """
    store = RawStore(brain)
    manifest = Manifest(store.brain)
    for path, relpath in _walk(sources):
        _ingest_one(path, relpath, store, manifest)

    log_manifest(store.brain, manifest)
    return manifest


def _ingest_one(path, relpath, store, manifest):
    source_format = SUPPORTED.get(os.path.splitext(path)[1].lower())
    if source_format is None:
        return manifest.add(Record(path, "unsupported", reason="no reader for this file type"))
    try:
        text = extract(path, source_format)
    except Exception as failure:            # one bad file never stops a corpus
        return manifest.add(Record(path, "failed", source_format=source_format,
                                   reason=str(failure)))

    if not text.strip():
        return manifest.add(Record(path, "empty", source_format=source_format,
                                   reason="no text in the file"))

    already = store.duplicate_of(text)
    if already:
        return manifest.add(Record(path, "duplicate", source_format=source_format,
                                   reason="same text as {}".format(already)))

    raw = store.add(text, os.path.splitext(relpath)[0], source=path,
                    source_format=source_format)
    return manifest.add(Record(path, "ok", raw=raw, words=len(text.split()),
                               source_format=source_format))


def extract(path, source_format):
    """The text of one source file, in the shape a reader would want it."""
    if source_format == "docx":
        return _extract_docx(path)
    if source_format == "csv":
        return _extract_csv(_read_text(path))
    if source_format == "json":
        return _extract_json(_read_text(path))
    return _read_text(path)


def _read_text(path):
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8", "replace")


def _extract_docx(path):
    """A `.docx` is a zip of XML — paragraphs are `w:p`, runs of text are `w:t`."""
    try:
        with zipfile.ZipFile(path) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ValueError("not a readable .docx — if it is DRM-protected or "
                                 "encrypted, the kit does not open it")
            document = archive.read("word/document.xml")
    except zipfile.BadZipFile:
        raise ValueError("not a readable .docx (corrupt or password-protected)")

    root = ElementTree.fromstring(document)
    paragraphs = []
    for paragraph in root.iter(WORD_NAMESPACE + "p"):
        text = "".join(node.text or "" for node in paragraph.iter(WORD_NAMESPACE + "t"))
        paragraphs.append(text.strip())
    return "\n\n".join(part for part in paragraphs if part)


def _extract_csv(text):
    """A table stays a table: a header row and its rows read far better than prose."""
    rows = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    header = _row(rows[0], width)
    divider = "| " + " | ".join(["---"] * width) + " |"
    return "\n".join([header, divider] + [_row(row, width) for row in rows[1:]])


def _row(row, width):
    cells = [cell.strip().replace("|", "\\|") for cell in row] + [""] * (width - len(row))
    return "| " + " | ".join(cells) + " |"


def _extract_json(text):
    """Re-indented so structure survives, fenced so it is never read as markdown."""
    return "```json\n{}\n```".format(json.dumps(json.loads(text), indent=2,
                                                ensure_ascii=False, sort_keys=False))


def _walk(sources):
    """Every candidate file under `sources`, with the name it will be filed as."""
    found = []
    for source in sources:
        source = os.path.abspath(os.path.expanduser(source))
        if os.path.isfile(source):
            found.append((source, os.path.basename(source)))
            continue
        for dirpath, dirnames, filenames in os.walk(source):
            dirnames[:] = sorted(name for name in dirnames if not name.startswith("."))
            for filename in sorted(filenames):
                if filename.startswith(".") or filename.startswith("~$"):
                    continue
                path = os.path.join(dirpath, filename)
                found.append((path, os.path.relpath(path, source)))
    return found


# --- cli -------------------------------------------------------------------

USAGE = "usage: ingest_local.py <path> [<path> ...] --into <brain-dir> [--json]\n"


def main(argv):
    try:
        paths, options = cli.scan(argv, options={"--into": None, "--json": False},
                                  flags=("--json",))
    except cli.UsageError as failure:
        sys.stderr.write("ingest_local.py: {}\n{}".format(failure, USAGE))
        return 2

    if not paths or not options["--into"]:
        sys.stderr.write(USAGE)
        return 2

    manifest = ingest(paths, options["--into"])
    print(json.dumps(manifest.as_dict(), indent=2)
          if options["--json"] else manifest.summary())
    if manifest.whole_corpus_failed:
        sys.stderr.write("ingest_local.py: nothing could be read — stop and talk to "
                         "the member rather than building an empty brain\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
