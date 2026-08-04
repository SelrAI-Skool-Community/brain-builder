#!/usr/bin/env python3
"""Stand an empty brain up on disk (spec.md §5).

    python3 scaffold.py --title "<title>" [--slug <slug>] [--domain <text>]
                        [--kind subject] [--stance <stance>] [--at <dir>]

Stdlib only.
"""
import datetime
import os
import re
import sys
import unicodedata

from brain_contract import parse_frontmatter

BRAINS_HOME = "~/brains"
DEFAULT_KIND = "subject"
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

    def read(self):
        """The full blueprint — read this before building, not before offering."""
        with open(self.path, "r", encoding="utf-8") as handle:
            return handle.read()

    def __repr__(self):
        return "Blueprint({!r})".format(self.kind)


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
                   stance=None):
    """Create an empty brain of `kind` and return its absolute root.

    Only the shape is written here. The one-liners, the wiki pages and the
    router are the build's job — but the `index.md` frontmatter is written now,
    in full, because `gen_router.py` reads the brain's identity off it and the
    router cannot be generated until it is there.
    """
    slug = slug or derive_slug(title)
    root = os.path.join(os.path.abspath(os.path.expanduser(at)), slug)
    if os.path.exists(root):
        raise FileExistsError("{}: already exists — pick another slug, or build "
                              "somewhere else".format(root))

    os.makedirs(os.path.join(root, "wiki"))
    os.makedirs(os.path.join(root, "raw"))
    _write(root, "index.md", _index(slug, title, _one_line(domain), kind,
                                    stance or default_stance(kind)))
    _write(root, "log.md", _log(title))
    _write(root, "CHANGELOG.md", _changelog(title))
    return root


def default_stance(kind):
    """Absent a blueprint's own declaration, only a persona speaks as someone."""
    return "persona" if kind == "persona" else "advisor"


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


def _log(title):
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
    options = {"--title": None, "--slug": None, "--domain": "",
               "--kind": DEFAULT_KIND, "--stance": None, "--at": BRAINS_HOME}
    pending = iter(argv[1:])
    for arg in pending:
        name, _, inline = arg.partition("=")
        if name == "--list-blueprints":
            for blueprint in list_blueprints():
                print("{}\t{}".format(blueprint.kind, blueprint.summary))
            return 0
        if name not in options:
            sys.stderr.write("scaffold.py: unknown argument {}\n{}".format(arg, USAGE))
            return 2
        value = inline if inline else next(pending, None)
        if value is None:
            sys.stderr.write("scaffold.py: {} needs a value\n".format(name))
            return 2
        options[name] = value

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
