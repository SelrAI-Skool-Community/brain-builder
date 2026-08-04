#!/usr/bin/env python3
"""Stand an empty brain up on disk (spec.md §5).

    python3 scaffold.py --title "<title>" [--slug <slug>] [--domain <text>]
                        [--kind subject] [--stance <stance>] [--at <dir>]
    python3 scaffold.py --list-blueprints

This module owns the mechanical half of a build's opening: where the brain goes,
what shape it starts in, and what it says about itself. Two decisions are worth
knowing about.

  frontmatter first  `index.md` is written with its full frontmatter — `slug`,
                     `title`, `domain`, `kind`, `stance` — before a single wiki
                     page exists, because `gen_router.py` reads the brain's
                     identity off exactly those fields. Deferring them would
                     leave the brain unroutable until the last phase.
  kinds are files    Blueprints are enumerated from `blueprints/` at runtime,
                     and a blueprint's declared stance is what the brain is
                     scaffolded with. Adding a kind is adding a file — no
                     script and no skill is edited when the next one lands.

It also owns `log.md` appends: this module creates that file, so it is also the
one place that writes to it, and ingest failures land there through `log_event`.

Stdlib only.
"""
import datetime
import os
import re
import sys
import unicodedata

import cli
from brain_contract import DEFAULT_KIND, default_stance, parse_frontmatter

BRAINS_HOME = "~/brains"
SLUG_MAX = 48
SLUG_FALLBACK = "brain"

#: Kinds are blueprints, not types — one file each, read at runtime.
BLUEPRINTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              os.pardir, "blueprints")


class Blueprint(object):
    """One brain kind, as the file that describes it."""

    def __init__(self, kind, summary, stance, path):
        self.kind = kind
        self.summary = summary
        self.stance = stance
        self.path = path


def list_blueprints(directory=BLUEPRINTS_DIR):
    """Every kind on offer, read off the blueprints directory at runtime.

    Enumerated rather than hardcoded so that adding a kind is adding a file:
    nothing in the builder skill needs editing when the next blueprint lands.
    A directory that is not there yet offers nothing — that is not an error.
    """
    directory = os.path.abspath(os.path.expanduser(directory))
    if not os.path.isdir(directory):
        return []
    blueprints = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".md") or name.startswith("."):
            continue
        path = os.path.join(directory, name)
        with open(path, "r", encoding="utf-8") as handle:
            front, _, _ = parse_frontmatter(handle.read())
        kind = _one_line(front.get("kind")) or os.path.splitext(name)[0]
        blueprints.append(Blueprint(
            kind=kind,
            summary=_one_line(front.get("summary")),
            stance=_one_line(front.get("stance")) or default_stance(kind),
            path=path,
        ))
    return blueprints

_DROPPED = re.compile(r"['‘’ʼ]")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def derive_slug(title, max_length=SLUG_MAX):
    """Turn a title into the folder name the brain will live under.

    Derived, never asked about: the plan gate *states* `~/brains/<slug>/` and
    moves on. Truncation stops at a word boundary so a shortened slug still
    reads as words rather than a cut-off syllable.
    """
    ascii_text = unicodedata.normalize("NFKD", _DROPPED.sub("", title or ""))
    ascii_text = ascii_text.encode("ascii", "ignore").decode("ascii").lower()
    slug = _NON_WORD.sub("-", ascii_text).strip("-")
    if not slug:
        return SLUG_FALLBACK
    if len(slug) <= max_length:
        return slug
    return slug[:max_length].rsplit("-", 1)[0].strip("-") or slug[:max_length].strip("-")


def scaffold_brain(title, at=BRAINS_HOME, slug=None, domain="", kind=DEFAULT_KIND,
                   stance=None, blueprints=BLUEPRINTS_DIR):
    """Create an empty brain of `kind` and return its absolute root.

    Only the shape is written here — the one-liners, the wiki pages and the
    router are the build's job. The stance is not asked for: it comes off the
    blueprint for `kind`, so a blueprint that declares one gets it without any
    caller passing it through. An explicit `stance` still wins, for the custom
    shapes that are honoured on opt-out.
    """
    slug = slug or derive_slug(title)
    stance = stance or blueprint_stance(kind, blueprints)
    root = os.path.join(os.path.abspath(os.path.expanduser(at)), slug)
    if os.path.exists(root):
        raise FileExistsError("{}: already exists — pick another slug, or build "
                              "somewhere else".format(root))

    os.makedirs(os.path.join(root, "wiki"))
    os.makedirs(os.path.join(root, "raw"))
    _write(root, "index.md", _index(slug, title, _one_line(domain), kind, stance))
    _write(root, "log.md", _log_page(title))
    _write(root, "CHANGELOG.md", _changelog(title))
    return root


def blueprint_stance(kind, directory=BLUEPRINTS_DIR):
    """The stance the blueprint for `kind` declares, or the contract's default.

    Reading it from the file is what makes a new kind a one-file change: a
    blueprint that declares `stance: coach` scaffolds a coach brain, and the
    router renders it, without a line of this script changing.
    """
    for blueprint in list_blueprints(directory):
        if blueprint.kind == kind:
            return blueprint.stance
    return default_stance(kind)


def log_event(root, message):
    """Append one line to the brain's `log.md`.

    Ingest failures land here rather than stopping the build: a dead source is
    a line in the log, not the end of the run.
    """
    path = os.path.join(os.path.abspath(os.path.expanduser(root)), "log.md")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("- {} — {}\n".format(_today(), message))
    return path


def _write(root, relpath, text):
    with open(os.path.join(root, relpath), "w", encoding="utf-8") as handle:
        handle.write(text)


def _one_line(text):
    if isinstance(text, (list, tuple)):
        text = " ".join(str(part) for part in text)
    return re.sub(r"\s+", " ", str(text) if text is not None else "").strip()


def _today():
    return datetime.date.today().isoformat()


def _index(slug, title, domain, kind, stance):
    return (
        "---\n"
        "type: index\n"
        "slug: {slug}\n"
        "title: {title}\n"
        "domain: {domain}\n"
        "kind: {kind}\n"
        "stance: {stance}\n"
        "---\n\n"
        "# {title}\n\n"
        "The map. One-liners carry the real numbers — routing happens on those,\n"
        "not on filenames.\n\n"
        "## The wiki\n\n"
        "<!-- One line per page, in the order a reader would meet them: a markdown\n"
        "     link to the page under wiki/, an em dash, then the page's actual\n"
        "     numbers — not a topic label. A one-liner that could describe any page\n"
        "     is a routing failure. Placeholder links are not left behind: lint\n"
        "     resolves every link in this file. -->\n\n"
        "## Known gaps\n\n"
        "<!-- What sits inside this brain's domain and is NOT covered, in a line each.\n"
        "     This is the register refusal fires from, so it is written honestly:\n"
        "     thin corpus areas, sources that failed, questions asked at intake that\n"
        "     the material never answered. -->\n"
    ).format(slug=slug, title=title, domain=domain or title, kind=kind, stance=stance)


def _log_page(title):
    return (
        "---\n"
        "type: log\n"
        "---\n\n"
        "# {title} — build and write-back log\n\n"
        "- {today} — brain scaffolded.\n"
    ).format(title=title, today=_today())


def _changelog(title):
    return "# {title}\n\n## {today}\n\n- Brain scaffolded.\n".format(
        title=title, today=_today())


# --- cli -------------------------------------------------------------------

USAGE = ("usage: scaffold.py --title <title> [--slug <slug>] [--domain <text>]\n"
         "                   [--kind <kind>] [--stance <stance>] [--at <dir>]\n"
         "       scaffold.py --list-blueprints\n")


def main(argv):
    try:
        _, options = cli.scan(
            argv,
            options={"--title": None, "--slug": None, "--domain": "",
                     "--kind": DEFAULT_KIND, "--stance": None, "--at": BRAINS_HOME,
                     "--list-blueprints": False},
            flags=("--list-blueprints",))
    except cli.UsageError as failure:
        sys.stderr.write("scaffold.py: {}\n{}".format(failure, USAGE))
        return 2

    if options["--list-blueprints"]:
        for blueprint in list_blueprints():
            print("{}\t{}".format(blueprint.kind, blueprint.summary))
        return 0

    if not options["--title"]:
        sys.stderr.write(USAGE)
        return 2
    try:
        root = scaffold_brain(title=options["--title"], at=options["--at"],
                              slug=options["--slug"], domain=options["--domain"],
                              kind=options["--kind"], stance=options["--stance"])
    except (OSError, ValueError) as failure:
        sys.stderr.write("scaffold.py: {}\n".format(failure))
        return 1
    print(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
