"""The on-disk brain contract, as data both `lint.py` and `gen_router.py` read.

A brain is a folder of markdown (spec.md §2):

    <slug>/
      SKILL.md        the generated router — the brain's whole interface (§3)
      index.md        the map: one-liners carrying real numbers, + ## Known gaps
      wiki/           the synthesized knowledge base; interior taxonomy free
      raw/            immutable ingested source material, fenced, in-tree
      log.md          build + write-back timeline
      CHANGELOG.md
      persona/        optional overlay: voice.md + exemplars.md
      standing/       optional overlay: standing facts and policies

`SKILL.md` + `index.md` + `wiki/` are the mandatory minimum for a folder to be a
brain. Everything else is optional, and folders this module has never heard of
are left alone — a brain carrying an unimagined shape is still a brain.

Stdlib only, on purpose: the kit ships to members with zero infrastructure.
"""
import os
import re

MANDATORY_FILES = ("SKILL.md", "index.md")
MANDATORY_DIRS = ("wiki",)
OPTIONAL_FILES = ("log.md", "CHANGELOG.md")
OPTIONAL_DIRS = ("raw",)
OVERLAY_DIRS = ("persona", "standing")

#: `persona/` is loaded whole and never cited; `standing/` is unfenced and
#: routed like `wiki/`. Named so the difference is stated once (spec.md §4).
PERSONA_OVERLAY, STANDING_OVERLAY = OVERLAY_DIRS

#: The kind a brain is when nothing says otherwise.
DEFAULT_KIND = "subject"

#: The two kinds that carry rules of their own. Named rather than spelled out at
#: each test site: kinds are an open taxonomy, and a bare string comparison
#: scattered through the router is how a fourth kind ends up half-supported.
PERSONA_KIND = "persona"
BUSINESS_KIND = "business"

#: OKF reserves these names, and reserves them for the brain root.
RESERVED_TYPES = {"index.md": "index", "log.md": "log"}

VOLATILITY_VALUES = ("fast", "slow", "stable")

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)(?:\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)>\s]+)>?\s*\)")
_FENCED_BLOCK = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)


class Page(object):
    """One markdown page: its frontmatter, its body, and where it lives."""

    def __init__(self, path, relpath, frontmatter, body, has_frontmatter):
        self.path = path
        self.relpath = relpath
        self.frontmatter = frontmatter
        self.body = body
        self.has_frontmatter = has_frontmatter

    @property
    def type(self):
        return self.frontmatter.get("type")

    @property
    def overlay(self):
        """The overlay this page sits in, or `""` for `wiki/` and the root."""
        folder = self.relpath.split("/")[0]
        return folder if folder in OVERLAY_DIRS else ""

    @property
    def in_overlay(self):
        return bool(self.overlay)

    @property
    def is_routed(self):
        """Whether an answer can reach this page by following links.

        The two overlays have different contracts (spec.md §4) and collapsing
        them is how `standing/` ends up cited in a Sources block without ever
        being held to the frontmatter rules. `persona/` is loaded whole and
        never cited; `standing/` is **unfenced** — routed exactly like `wiki/`,
        linked from `index.md` — so it is a routed page and the page rules bind
        it.
        """
        return self.overlay != PERSONA_OVERLAY

    def links(self):
        """Relative link targets in the body, code blocks excluded."""
        prose = _FENCED_BLOCK.sub("", self.body)
        targets = []
        for target in _LINK.findall(prose):
            if "://" in target or target.startswith(("#", "mailto:", "tel:")):
                continue
            targets.append(target)
        return targets


def parse_frontmatter(text):
    """Split a leading YAML frontmatter block off `text`.

    Returns `(mapping, body, present)`. The mapping covers the subset a brain
    needs — `key: value` scalars, one level of nesting, `- item` lists, and
    `>`/`|` block scalars. Anything richer is out of contract by design.
    """
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text, False
    return _parse_block(match.group(1)), text[match.end():], True


def _parse_block(block):
    lines = [line.rstrip() for line in block.split("\n")
             if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        return {}
    mapping, _ = _parse_mapping(lines, 0, _indent(lines[0]))
    return mapping


def _parse_mapping(lines, index, indent):
    """Read `key: value` pairs at `indent` until the block ends or outdents."""
    mapping = {}
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if _indent(line) < indent or stripped.startswith("- "):
            break
        if ":" not in stripped:
            index += 1
            continue
        key, _, value = stripped.partition(":")
        own_indent = _indent(line)
        index += 1
        if value.strip() in (">", "|", ">-", "|-"):
            mapping[key.strip()], index = _read_block_scalar(lines, index, own_indent)
        elif value.strip() == "":
            mapping[key.strip()], index = _parse_child(lines, index, own_indent)
        else:
            mapping[key.strip()] = _scalar(value)
    return mapping, index


def _parse_child(lines, index, parent_indent):
    """What follows a bare `key:` — a list, a nested mapping, or nothing."""
    if index >= len(lines):
        return "", index
    line = lines[index]
    own_indent = _indent(line)
    if line.strip().startswith("- ") and own_indent >= parent_indent:
        return _parse_sequence(lines, index, own_indent)
    if own_indent > parent_indent:
        return _parse_mapping(lines, index, own_indent)
    return "", index


def _parse_sequence(lines, index, indent):
    items = []
    while index < len(lines):
        line = lines[index]
        if _indent(line) != indent or not line.strip().startswith("- "):
            break
        items.append(_scalar(line.strip()[2:]))
        index += 1
    return items, index


def _read_block_scalar(lines, index, indent):
    collected = []
    while index < len(lines) and _indent(lines[index]) > indent:
        collected.append(lines[index].strip())
        index += 1
    return " ".join(part for part in collected if part), index


def _indent(line):
    return len(line) - len(line.lstrip())


def _scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_scalar(part) for part in inner.split(",")] if inner else []
    return value


def read_page(root, relpath):
    path = os.path.join(root, relpath)
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    frontmatter, body, present = parse_frontmatter(text)
    return Page(path, relpath.replace(os.sep, "/"), frontmatter, body, present)


def contract_pages(root):
    """Every markdown page the contract governs — `raw/` and SKILL.md excluded.

    `raw/` is fenced, so it is never parsed. Unrecognised folders are not part
    of the contract either: only `index.md`, `log.md`, `wiki/` and the declared
    overlays are walked.
    """
    pages = []
    for name in sorted(RESERVED_TYPES):
        if os.path.isfile(os.path.join(root, name)):
            pages.append(read_page(root, name))
    for folder in MANDATORY_DIRS + OVERLAY_DIRS:
        base = os.path.join(root, folder)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            for filename in sorted(filenames):
                if not filename.endswith(".md"):
                    continue
                full = os.path.join(dirpath, filename)
                pages.append(read_page(root, os.path.relpath(full, root)))
    return pages


def default_stance(kind, overlays=()):
    """The stance a brain holds when it has not declared one.

    One rule, in one place: the builder writes a stance into `index.md` and the
    router reads it back, and the two disagreeing is how a persona brain ends up
    answering as an advisor. A *declared* stance always wins over this — stances
    are extensible, and this is not a list of two.
    """
    if kind == PERSONA_KIND or OVERLAY_DIRS[0] in overlays:
        return PERSONA_KIND
    return "advisor"


def is_iso_date(value):
    return bool(_ISO_DATE.match(value or ""))
