#!/usr/bin/env python3
"""Check a brain's figures before they become citable facts (spec.md §6).

    python3 verify_numbers.py <brain-dir> [--json]
    python3 verify_numbers.py <file> [<file> ...] [--json]

ASR corrupts exactly the names and figures that matter, and a corrupted figure
is worse in a brain than a missing one: the router answers with flat certainty
on the brain's own facts, so a wrong number is stated as confidently as a right
one. The defence is the arithmetic already sitting around the figure — a claim
that contradicts its own sentence is catchable without leaving the page.

Four checks, and the reason each one earns its place:

  arithmetic  "20 % of 300 is 45" contradicts itself. So does a stated sum, and
              a ratio restated as a percentage. These are `error`s: a figure
              that fails here does not get softened, it comes out of the brain.
  range       "between 250 and 200" has one end wrong, whichever end it is.
  spoken      "fifteen (50)" is the ASR failure written down — the words and the
              digits disagreeing inside one sentence.
  unscaled    a figure with nothing attached to it. `warn`, not `error`: pages
              are meant to note the scale and context of their data, and "the
              oven holds 250" has lost the half of the fact that made it useful.

And one page-level check in the same spirit: a wiki page carrying figures with
no `sources` in its frontmatter has no chain back to `raw/`, so its numbers are
not yet citable.

Deliberately literal. Every check reads one sentence and compares two numbers
the sentence itself supplies; nothing here infers, and nothing here rewrites. A
finding is something for a human or the build to look at, and `raw/` is never
touched.

Stdlib only.
"""
import json
import os
import re
import sys

import cli
from brain_contract import parse_frontmatter, read_page
from scaffold import log_event

#: Below this, a bare number is a count in a sentence, not an unscaled measure.
MIN_SCALED_FIGURE = 100

#: Years are dates, not measurements.
YEAR_RANGE = (1900, 2099)

#: How far a stated figure may sit from the arithmetic before it is wrong.
#: Proportional, with a floor so rounded percentages are not chased.
RELATIVE_TOLERANCE = 0.02
ABSOLUTE_TOLERANCE = 0.5

#: Frontmatter that chains a page's figures back to `raw/`.
PROVENANCE_FIELDS = ("sources", "source", "distilled_from")

_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_SCALE = r"(?:million|billion|thousand|bn|k|m)"

_PERCENT_OF = re.compile(
    r"(?P<pct>{n})\s*(?:%|per\s?cent)\s+of\s+(?:the\s+)?(?P<total>{n})\s*"
    r"(?P<tscale>{s})?\s+(?:is|are|was|were|=|equals?)\s+(?P<result>{n})\s*"
    r"(?P<rscale>{s})?".format(n=_NUMBER, s=_SCALE), re.IGNORECASE)

_SUM = re.compile(
    r"(?P<a>{n})\s*(?:\+|plus)\s*(?P<b>{n})\s*(?:=|is|are|was|makes|gives|equals?)"
    r"\s*(?P<c>{n})".format(n=_NUMBER), re.IGNORECASE)

_RATIO_PERCENT = re.compile(
    r"(?P<part>{n})\s+(?:out\s+)?of\s+(?:the\s+)?(?P<whole>{n})\b[^.\n]{{0,80}}?"
    r"\(\s*(?P<pct>{n})\s*%\s*\)".format(n=_NUMBER), re.IGNORECASE)

_RANGE = re.compile(
    r"between\s+(?P<low>{n})\s*(?:%|degrees?|°[cf]?)?\s+and\s+(?P<high>{n})".format(
        n=_NUMBER), re.IGNORECASE)

_FIGURE = re.compile(r"(?P<currency>[$£€])?\s?(?P<value>{n})".format(n=_NUMBER))
_UNIT_FOLLOWS = re.compile(r"\s*(%|per\s?cent|[A-Za-z°])")

_SCALES = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6,
           "billion": 1e9, "bn": 1e9}

_ONES = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
         "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
         "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_MULTIPLIERS = {"hundred": 100, "thousand": 1000, "million": 10 ** 6,
                "billion": 10 ** 9}

_NUMBER_WORD = "|".join(sorted(list(_ONES) + list(_MULTIPLIERS), key=len, reverse=True))
_SPOKEN = re.compile(
    r"\b(?P<words>(?:{w})(?:[\s-]+(?:and[\s-]+)?(?:{w}))*)\s*\(\s*(?P<digits>{n})\s*\)"
    .format(w=_NUMBER_WORD, n=_NUMBER), re.IGNORECASE)


class Finding(object):
    """One figure worth a second look, and why."""

    def __init__(self, kind, severity, message, excerpt, source=""):
        self.kind = kind
        self.severity = severity
        self.message = message
        self.excerpt = excerpt
        self.source = source

    def line(self):
        return "{:<6} {}{} — {}".format(
            self.severity.upper(), self.source + ": " if self.source else "",
            self.message, self.excerpt)

    def as_dict(self):
        return {"kind": self.kind, "severity": self.severity, "source": self.source,
                "message": self.message, "excerpt": self.excerpt}


class Report(object):
    """Every figure the pass wants looked at, across whatever it was pointed at."""

    def __init__(self, target, pages, findings):
        self.target = target
        self.pages = pages
        self.findings = findings

    @property
    def errors(self):
        return [finding for finding in self.findings if finding.severity == "error"]

    @property
    def warnings(self):
        return [finding for finding in self.findings if finding.severity == "warn"]

    @property
    def ok(self):
        return not self.errors

    def summary(self):
        if not self.findings:
            return "no figure problems across {} pages".format(self.pages)
        return "{} figure(s) to check across {} pages — {} error(s), {} warning(s)".format(
            len(self.findings), self.pages, len(self.errors), len(self.warnings))

    def render(self):
        return "\n".join([finding.line() for finding in self.findings] + [self.summary()])

    def as_dict(self):
        return {"target": self.target, "pages": self.pages, "summary": self.summary(),
                "findings": [finding.as_dict() for finding in self.findings]}


def verify(text, source=""):
    """Every figure in `text` that its own sentence contradicts, or that lost its scale."""
    findings = []
    findings += _check_percent_of(text, source)
    findings += _check_sums(text, source)
    findings += _check_ratio_percent(text, source)
    findings += _check_ranges(text, source)
    findings += _check_spoken(text, source)
    findings += _check_scale(text, source)
    return findings


def verify_brain(brain, log=False):
    """Check `index.md` and every `wiki/` page. `raw/` is source, not claim.

    `raw/` is deliberately skipped: a transcript is allowed to contain a speaker
    misspeaking, and quarantining the wiki from that is the wiki's job. `log.md`
    is skipped for the same reason — it is a timeline, not a claim.
    """
    brain = os.path.abspath(os.path.expanduser(brain))
    findings, pages = [], 0
    for relpath in _pages_of(brain):
        pages += 1
        page = read_page(brain, relpath)
        findings += verify(page.body, relpath)
        if relpath.startswith("wiki/"):
            findings += _check_provenance(page, relpath)
    report = Report(brain, pages, findings)
    if log and os.path.isfile(os.path.join(brain, "log.md")):
        log_event(brain, "verify: " + report.summary())
    return report


def verify_files(paths):
    """Check loose markdown files, for the spot-checks Phase 4 runs by hand."""
    findings, pages = [], 0
    for path in paths:
        with open(path, "r", encoding="utf-8") as handle:
            _, body, _ = parse_frontmatter(handle.read())
        pages += 1
        findings += verify(body, os.path.basename(path))
    return Report(", ".join(paths), pages, findings)


def words_to_number(phrase):
    """The value of a spoken number — `"two hundred and fifty"` — or `None`."""
    total, current, seen = 0, 0, False
    for word in re.split(r"[\s-]+", (phrase or "").lower()):
        if word in ("and", ""):
            continue
        if word in _ONES:
            current += _ONES[word]
            seen = True
        elif word in _MULTIPLIERS:
            multiplier = _MULTIPLIERS[word]
            if multiplier >= 1000:
                total += max(current, 1) * multiplier
                current = 0
            else:
                current = max(current, 1) * multiplier
            seen = True
        else:
            return None
    return total + current if seen else None


def parse_number(text, scale=None):
    """A figure written the way prose writes them: `1,200`, `3.5`, `2 million`."""
    value = float(str(text).replace(",", "").strip())
    if scale:
        value *= _SCALES.get(scale.lower(), 1)
    return value


def _check_percent_of(text, source):
    findings = []
    for match in _PERCENT_OF.finditer(text):
        total = parse_number(match.group("total"), match.group("tscale"))
        stated = parse_number(match.group("result"), match.group("rscale"))
        expected = total * parse_number(match.group("pct")) / 100.0
        if _off(expected, stated):
            findings.append(Finding(
                "arithmetic", "error",
                "the arithmetic gives {:g}, the page says {:g}".format(expected, stated),
                match.group(0).strip(), source))
    return findings


def _check_sums(text, source):
    findings = []
    for match in _SUM.finditer(text):
        expected = parse_number(match.group("a")) + parse_number(match.group("b"))
        stated = parse_number(match.group("c"))
        if _off(expected, stated):
            findings.append(Finding(
                "arithmetic", "error",
                "the sum is {:g}, the page says {:g}".format(expected, stated),
                match.group(0).strip(), source))
    return findings


def _check_ratio_percent(text, source):
    findings = []
    for match in _RATIO_PERCENT.finditer(text):
        whole = parse_number(match.group("whole"))
        if not whole:
            continue
        expected = parse_number(match.group("part")) / whole * 100.0
        stated = parse_number(match.group("pct"))
        if _off(expected, stated):
            findings.append(Finding(
                "arithmetic", "error",
                "{:g} of {:g} is {:.1f} %, the page says {:g} %".format(
                    parse_number(match.group("part")), whole, expected, stated),
                match.group(0).strip(), source))
    return findings


def _check_ranges(text, source):
    findings = []
    for match in _RANGE.finditer(text):
        low, high = parse_number(match.group("low")), parse_number(match.group("high"))
        if high < low:
            findings.append(Finding(
                "range", "error",
                "the range runs backwards — {:g} is above {:g}".format(low, high),
                match.group(0).strip(), source))
    return findings


def _check_spoken(text, source):
    findings = []
    for match in _SPOKEN.finditer(text):
        spoken = words_to_number(match.group("words"))
        written = parse_number(match.group("digits"))
        if _off(spoken, written):
            findings.append(Finding(
                "spoken", "error",
                "the words say {:g}, the digits say {:g}".format(spoken, written),
                match.group(0).strip(), source))
    return findings


def _check_scale(text, source):
    """Figures with nothing attached — no unit, no currency, no percent sign.

    Deliberately lenient: any word directly after the figure counts as its
    context, because prose attaches units in too many shapes to enumerate. What
    is left is the blatant case — a number that ends its clause naked, which is
    what a figure looks like after its unit was lost in transcription.
    """
    findings = []
    for match in _FIGURE.finditer(text):
        if match.group("currency"):
            continue
        value = parse_number(match.group("value"))
        if value < MIN_SCALED_FIGURE or _is_year(match.group("value"), value):
            continue
        if _UNIT_FOLLOWS.match(text[match.end():]):
            continue
        findings.append(Finding(
            "unscaled", "warn",
            "{:g} carries no unit — note the scale of the figure, not just its source"
            .format(value), _sentence_around(text, match.start()), source))
    return findings


def _check_provenance(page, relpath):
    """A page with figures and no `sources` has no chain back to `raw/`."""
    if any(str(page.frontmatter.get(field) or "").strip() for field in PROVENANCE_FIELDS):
        return []
    if not _carries_figures(page.body):
        return []
    return [Finding("unsourced", "warn",
                    "carries figures but no `sources` frontmatter — nothing chains "
                    "them back to raw/", relpath, relpath)]


def _carries_figures(text):
    if "%" in text:
        return True
    return any(parse_number(match.group("value")) >= MIN_SCALED_FIGURE
               and not _is_year(match.group("value"), parse_number(match.group("value")))
               for match in _FIGURE.finditer(text))


def _is_year(raw, value):
    return "." not in raw and "," not in raw and YEAR_RANGE[0] <= value <= YEAR_RANGE[1]


def _off(expected, stated):
    return abs(expected - stated) > max(abs(expected) * RELATIVE_TOLERANCE,
                                        ABSOLUTE_TOLERANCE)


def _sentence_around(text, position):
    start = max(text.rfind(".", 0, position), text.rfind("\n", 0, position)) + 1
    end = text.find(".", position)
    end = len(text) if end == -1 else end + 1
    return " ".join(text[start:end].split())


def _pages_of(brain):
    relpaths = ["index.md"] if os.path.isfile(os.path.join(brain, "index.md")) else []
    wiki = os.path.join(brain, "wiki")
    for dirpath, dirnames, filenames in os.walk(wiki):
        dirnames.sort()
        for filename in sorted(filenames):
            if filename.endswith(".md"):
                relpaths.append(os.path.relpath(
                    os.path.join(dirpath, filename), brain).replace(os.sep, "/"))
    return relpaths


# --- cli -------------------------------------------------------------------

USAGE = ("usage: verify_numbers.py <brain-dir> [--json]\n"
         "       verify_numbers.py <file> [<file> ...] [--json]\n")


def main(argv):
    try:
        positional, options = cli.scan(argv, options={"--json": False}, flags=("--json",))
    except cli.UsageError as failure:
        sys.stderr.write("verify_numbers.py: {}\n{}".format(failure, USAGE))
        return 2

    if not positional:
        sys.stderr.write(USAGE)
        return 2

    target = os.path.expanduser(positional[0])
    try:
        if len(positional) == 1 and os.path.isdir(target):
            report = verify_brain(target, log=True)
        else:
            report = verify_files([os.path.expanduser(path) for path in positional])
    except OSError as failure:
        sys.stderr.write("verify_numbers.py: {}\n".format(failure))
        return 1

    print(json.dumps(report.as_dict(), indent=2) if options["--json"] else report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
