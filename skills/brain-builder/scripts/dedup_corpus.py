#!/usr/bin/env python3
"""Find the sources that restate each other (spec.md §6, corpus-level dedup).

    python3 dedup_corpus.py <brain-dir> [--threshold 0.6] [--json]

The ingest arms drop text they have seen byte for byte. This pass catches what
that cannot see, and what the prototype actually hit: a "best of" compilation
that retells three episodes almost word for word. Distilled naively, the same
claim lands on four `raw/` pages and the wiki reads it as four independent
sources agreeing — which is exactly the kind of false confidence a brain is
supposed to be immune to.

**Measured as shingles.** Every source becomes the set of its overlapping
five-word runs. Two numbers come out of a pair, and they mean different things:

  containment  how much of the *smaller* source sits inside the larger. High
               containment with low similarity is the compilation shape.
  jaccard      how much the two share overall. High similarity is the
               re-upload / re-cut shape, where neither is really the original.

**It reports; it never deletes.** `raw/` is immutable (spec.md §2), so the
output is a finding for the taxonomy pass to distil once, plus a line in
`log.md`. Repetition in a corpus is not an error and this never exits non-zero
because of it.

Stdlib only.
"""
import hashlib
import json
import os
import re
import sys

import cli
from brain_contract import parse_frontmatter
from scaffold import log_event

#: Five-word runs: long enough that unrelated prose never collides, short enough
#: that a retelling with a few words swapped still overlaps heavily.
SHINGLE_WORDS = 5

#: Above this, two sources are telling the same story. Tuned to catch a lightly
#: reworded retelling without flagging two talks on one topic.
DEFAULT_THRESHOLD = 0.6

_WORD = re.compile(r"[^\w']+")


class Overlap(object):
    """How much two sources have in common, in the two ways that matter."""

    def __init__(self, containment, jaccard):
        self.containment = containment
        self.jaccard = jaccard

    @classmethod
    def between(cls, left, right):
        """The overlap between two shingle sets. Empty sets share nothing."""
        if not left or not right:
            return cls(0.0, 0.0)
        shared = len(left & right)
        return cls(containment=shared / float(min(len(left), len(right))),
                   jaccard=shared / float(len(left | right)))

    def verdict(self, threshold):
        """What kind of restating this is, or `None` if it is not restating."""
        if self.jaccard >= threshold:
            return "near-duplicate"
        if self.containment >= threshold:
            return "contained"
        return None


class Pair(object):
    """One source that restates another, and what kind of restating it is."""

    def __init__(self, duplicate, original, overlap, verdict):
        self.duplicate = duplicate
        self.original = original
        self.overlap = overlap
        self.verdict = verdict

    def line(self):
        return "{} is {} in {} ({:.0%} shared)".format(
            self.duplicate,
            "restated" if self.verdict == "near-duplicate" else "contained",
            self.original, self.overlap.containment)

    def as_dict(self):
        return {"duplicate": self.duplicate, "original": self.original,
                "verdict": self.verdict,
                "containment": round(self.overlap.containment, 3),
                "jaccard": round(self.overlap.jaccard, 3)}


class Report(object):
    """What the pass found across one brain's `raw/`."""

    def __init__(self, brain, sources, pairs):
        self.brain = brain
        self.sources = sources
        self.pairs = pairs

    def summary(self):
        if not self.pairs:
            return "no near-duplicates across {} sources".format(self.sources)
        return "{} near-duplicate pair{} across {} sources — {}".format(
            len(self.pairs), "" if len(self.pairs) == 1 else "s", self.sources,
            "; ".join(pair.line() for pair in self.pairs))

    def as_dict(self):
        return {"brain": self.brain, "sources": self.sources,
                "summary": self.summary(),
                "pairs": [pair.as_dict() for pair in self.pairs]}


def shingles(text, size=SHINGLE_WORDS):
    """The set of overlapping word-runs in `text`, hashed to keep the set small."""
    words = [word for word in _WORD.split((text or "").lower()) if word]
    if len(words) < size:
        return set()
    return {hashlib.blake2b(" ".join(words[index:index + size]).encode("utf-8"),
                            digest_size=8).digest()
            for index in range(len(words) - size + 1)}


def compare(first, second, size=SHINGLE_WORDS):
    """The overlap between two sources. Sources too short to shingle share nothing."""
    return Overlap.between(shingles(first, size), shingles(second, size))


def find_near_duplicates(pages, threshold=DEFAULT_THRESHOLD, size=SHINGLE_WORDS):
    """Every pair of `(name, text)` that restates the other, above `threshold`."""
    prepared = [(name, shingles(text, size)) for name, text in pages]
    pairs = []
    for index, (name, left) in enumerate(prepared):
        for other, right in prepared[index + 1:]:
            overlap = Overlap.between(left, right)
            verdict = overlap.verdict(threshold)
            if not verdict:
                continue
            smaller, larger = ((name, other) if len(left) <= len(right)
                               else (other, name))
            pairs.append(Pair(smaller, larger, overlap, verdict))
    return pairs


def scan(brain, threshold=DEFAULT_THRESHOLD, log=False):
    """Compare every `raw/` page in `brain` against every other."""
    brain = os.path.abspath(os.path.expanduser(brain))
    pages = read_raw(brain)
    report = Report(brain, len(pages), find_near_duplicates(pages, threshold))
    if log and os.path.isfile(os.path.join(brain, "log.md")):
        log_event(brain, "dedup: " + report.summary())
    return report


def read_raw(brain):
    """Every `raw/` page as `(brain-relative path, body)` — frontmatter dropped.

    Provenance headers are near-identical across an arm's pages by design, so
    counting them would make every YouTube video look like every other one.
    """
    directory = os.path.join(brain, "raw")
    if not os.path.isdir(directory):
        return []
    pages = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
            _, body, _ = parse_frontmatter(handle.read())
        pages.append(("raw/" + name, body))
    return pages


# --- cli -------------------------------------------------------------------

USAGE = "usage: dedup_corpus.py <brain-dir> [--threshold <0-1>] [--json]\n"


def main(argv):
    try:
        positional, options = cli.scan(
            argv, options={"--threshold": DEFAULT_THRESHOLD, "--json": False},
            flags=("--json",))
        threshold = float(options["--threshold"])
    except (cli.UsageError, ValueError) as failure:
        sys.stderr.write("dedup_corpus.py: {}\n{}".format(failure, USAGE))
        return 2

    if len(positional) != 1:
        sys.stderr.write(USAGE)
        return 2
    if not os.path.isdir(os.path.expanduser(positional[0])):
        sys.stderr.write("dedup_corpus.py: {}: not a directory\n".format(positional[0]))
        return 1

    report = scan(positional[0], threshold=threshold, log=True)
    if options["--json"]:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(report.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
