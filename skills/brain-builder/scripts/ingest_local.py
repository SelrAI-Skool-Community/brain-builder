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
the likeliest way to reach it, and silently building an empty brain would be the
worst possible answer.

Dedup here is **exact**: identical text, whitespace-normalised. Near-verbatim
dedup (spec.md §6) is a transcript problem — compilations restating other
episodes — and belongs to the arms that ingest transcripts, not to this one.

`raw/` is immutable, so a second run never overwrites a page a first run wrote:
what is already in `raw/` is read back, and a source already ingested comes out
as a duplicate rather than a clobbered file.

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

import cli
from brain_contract import parse_frontmatter
from scaffold import derive_slug, log_event

TEXT_FORMATS = {".md": "md", ".markdown": "md", ".txt": "txt", ".text": "txt"}
SUPPORTED = dict(TEXT_FORMATS, **{".csv": "csv", ".json": "json", ".docx": "docx"})

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


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

    #: Everything that can become of a source file. `ok` is the one that lands.
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
        """Files were found and none of their text is in the brain.

        The only condition that stops a build. Unsupported files count towards
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


def ingest(sources, brain):
    """Ingest `sources` (files or folders) into `brain`'s `raw/`. Never raises.

    Returns a `Manifest`. Anything that failed is on it and in the brain's
    `log.md`, so the build can narrate counts and move on. Re-running against a
    brain that already holds material adds to it — `raw/` is immutable, and
    nothing already ingested is rewritten.
    """
    brain = os.path.abspath(os.path.expanduser(brain))
    raw_dir = os.path.join(brain, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    manifest = Manifest(brain)
    used_names, seen_text = _already_ingested(raw_dir)
    for path, relpath in _walk(sources):
        _ingest_one(path, relpath, raw_dir, manifest, seen_text, used_names)

    _log_manifest(brain, manifest)
    return manifest


def _already_ingested(raw_dir):
    """What a previous run left in `raw/`: the names taken and the text held.

    Read back rather than assumed, so a Gate 1 edit that adds a folder and
    re-runs cannot overwrite a page — `raw/` is immutable (spec.md §2).
    """
    used_names, seen_text = set(), {}
    for name in sorted(os.listdir(raw_dir)):
        if not name.endswith(".md"):
            continue
        used_names.add(name)
        with open(os.path.join(raw_dir, name), "r", encoding="utf-8") as handle:
            front, body, _ = parse_frontmatter(handle.read())
        seen_text[_digest(body)] = front.get("source") or "raw/" + name
    return used_names, seen_text


def _digest(text):
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()


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

    digest = _digest(text)
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
    """The `raw/` filename for a source, kept unique across the whole corpus."""
    stem = derive_slug(os.path.splitext(relpath)[0]) or "source"
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


def _log_manifest(brain, manifest):
    """Write the run's counts and every non-landing source into `log.md`."""
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
