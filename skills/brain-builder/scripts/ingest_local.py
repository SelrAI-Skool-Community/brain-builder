#!/usr/bin/env python3
"""Ingest local files into a brain's `raw/` (spec.md §6, local-files arm).

    python3 ingest_local.py <path> [<path> ...] --into <brain-dir> [--json]

Handles md/txt/csv/json/docx. Every ingested file becomes one attributed page
under `raw/`: the source path and the ingest date ride with the text, because
the rights stance is that every chunk in a brain says where it came from.

Failure is a record, not an exception. A file that cannot be read, or that holds
no text at all, is counted and logged to the brain's `log.md`, and the run
carries on — one dead file has never been a reason to abandon a corpus. The one
exception is a corpus where *nothing* worked, which exits non-zero so the build
stops rather than producing an empty brain.

Stdlib only: `.docx` is a zip of XML, which `zipfile` and `ElementTree` read
without a third-party library.
"""
import csv
import datetime
import hashlib
import io
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ElementTree

from scaffold import log_event

TEXT_FORMATS = {".md": "md", ".markdown": "md", ".txt": "txt", ".text": "txt"}
SUPPORTED = dict(TEXT_FORMATS, **{".csv": "csv", ".json": "json", ".docx": "docx"})

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_NON_WORD = re.compile(r"[^a-z0-9]+")


class Record(object):
    """One source file and what became of it."""

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

    OUTCOMES = ("ok", "empty", "duplicate", "unsupported", "failed")

    def __init__(self, brain):
        self.brain = brain
        self.records = []

    def add(self, record):
        self.records.append(record)
        return record

    def _of(self, outcome):
        return [record for record in self.records if record.outcome == outcome]

    ok = property(lambda self: self._of("ok"))
    empty = property(lambda self: self._of("empty"))
    duplicate = property(lambda self: self._of("duplicate"))
    unsupported = property(lambda self: self._of("unsupported"))
    failed = property(lambda self: self._of("failed"))

    @property
    def words(self):
        return sum(record.words for record in self.ok)

    @property
    def counts(self):
        counts = {outcome: len(self._of(outcome)) for outcome in self.OUTCOMES}
        counts["words"] = self.words
        return counts

    @property
    def considered(self):
        """Everything the run looked at — unsupported files were never candidates."""
        return [record for record in self.records if record.outcome != "unsupported"]

    @property
    def whole_corpus_failed(self):
        """Nothing usable came out. The only condition that stops a build."""
        return bool(self.considered) and not self.ok

    def summary(self):
        """The one line the build narrates, and the one line the log keeps."""
        parts = ["{} sources ingested ({:,} words)".format(len(self.ok), self.words)]
        for outcome, label in (("empty", "empty"), ("duplicate", "duplicate"),
                               ("unsupported", "unsupported"), ("failed", "failed")):
            found = self._of(outcome)
            if found:
                parts.append("{} {}".format(len(found), label))
        return ", ".join(parts)

    def as_dict(self):
        return {"brain": self.brain, "counts": self.counts,
                "summary": self.summary(),
                "records": [record.as_dict() for record in self.records]}


def ingest(sources, brain, log=True):
    """Ingest `sources` (files or folders) into `brain`'s `raw/`. Never raises.

    Returns a `Manifest`. Anything that failed is on it, and — when `log` is on
    — in the brain's `log.md`, so the build can narrate counts and move on.
    """
    brain = os.path.abspath(os.path.expanduser(brain))
    raw_dir = os.path.join(brain, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    manifest = Manifest(brain)
    seen_text, used_names = {}, set()
    for path, relpath in _walk(sources):
        _ingest_one(path, relpath, raw_dir, manifest, seen_text, used_names)

    if log:
        _log(brain, manifest)
    return manifest


def _ingest_one(path, relpath, raw_dir, manifest, seen_text, used_names):
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

    digest = hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()
    if digest in seen_text:
        return manifest.add(Record(path, "duplicate", source_format=source_format,
                                   reason="same text as {}".format(seen_text[digest])))
    seen_text[digest] = path

    name = _raw_name(relpath, used_names)
    with open(os.path.join(raw_dir, name), "w", encoding="utf-8") as handle:
        handle.write(_raw_page(path, source_format, text))
    return manifest.add(Record(path, "ok", raw="raw/" + name, words=len(text.split()),
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


def _raw_name(relpath, used_names):
    stem = _NON_WORD.sub("-", os.path.splitext(relpath)[0].lower()).strip("-") or "source"
    name, suffix = stem + ".md", 2
    while name in used_names:
        name, suffix = "{}-{}.md".format(stem, suffix), suffix + 1
    used_names.add(name)
    return name


def _raw_page(path, source_format, text):
    return ("---\n"
            "type: source\n"
            "source: {source}\n"
            "source_format: {source_format}\n"
            "ingested: {today}\n"
            "---\n\n"
            "{text}\n").format(source=path, source_format=source_format,
                               today=datetime.date.today().isoformat(),
                               text=text.strip())


def _log(brain, manifest):
    if not os.path.isfile(os.path.join(brain, "log.md")):
        return
    log_event(brain, "ingest: " + manifest.summary())
    for record in manifest.records:
        if record.outcome in ("ok", "duplicate"):
            continue
        log_event(brain, "ingest {}: {} — {}".format(
            record.outcome, record.source, record.reason))


# --- cli -------------------------------------------------------------------

USAGE = "usage: ingest_local.py <path> [<path> ...] --into <brain-dir> [--json]\n"


def main(argv):
    paths, brain, as_json = [], None, False
    pending = iter(argv[1:])
    for arg in pending:
        name, _, inline = arg.partition("=")
        if name == "--into":
            brain = inline if inline else next(pending, None)
            if not brain:
                sys.stderr.write("ingest_local.py: --into needs a value\n")
                return 2
        elif name == "--json":
            as_json = True
        elif name.startswith("--"):
            sys.stderr.write("ingest_local.py: unknown argument {}\n{}".format(arg, USAGE))
            return 2
        else:
            paths.append(arg)

    if not paths or not brain:
        sys.stderr.write(USAGE)
        return 2

    manifest = ingest(paths, brain)
    print(json.dumps(manifest.as_dict(), indent=2) if as_json else manifest.summary())
    if manifest.whole_corpus_failed:
        sys.stderr.write("ingest_local.py: nothing could be read — stop and talk to "
                         "the member rather than building an empty brain\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
