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

#: OKF reserves these names, and reserves them for the brain root.
RESERVED_TYPES = {"index.md": "index", "log.md": "log"}

#: `raw/` is immutable source material: never parsed, never linted, only quoted.
FENCED_DIRS = ("raw",)

VOLATILITY_VALUES = ("fast", "slow", "stable")

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
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
    root = {}
    stack = [(-1, root)]
    pending = None  # (container, key, indent) awaiting an indented list or scalar
    lines = block.split("\n")
    index = 0
    while index < len(lines):
        raw = lines[index].rstrip()
        index += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        stripped = raw.strip()

        if stripped.startswith("- "):
            if pending is None:
                continue
            container, key, _ = pending
            container.setdefault(key, [])
            if isinstance(container[key], list):
                container[key].append(_scalar(stripped[2:]))
            continue

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()

        if value in (">", "|", ">-", "|-"):
            folded, index = _read_block_scalar(lines, index, indent)
            container[key] = folded
            pending = None
        elif value == "":
            child = {}
            container[key] = child
            stack.append((indent, child))
            pending = (container, key, indent)
        else:
            container[key] = _scalar(value)
            pending = None
    _prune_empty_maps(root)
    return root


def _read_block_scalar(lines, index, indent):
    collected = []
    while index < len(lines):
        line = lines[index]
        if line.strip() and (len(line) - len(line.lstrip())) <= indent:
            break
        collected.append(line.strip())
        index += 1
    return " ".join(part for part in collected if part), index


def _prune_empty_maps(mapping):
    """A `key:` that got a list instead of children leaves an empty dict behind."""
    for key, value in list(mapping.items()):
        if isinstance(value, dict):
            _prune_empty_maps(value)
            if not value:
                mapping[key] = ""


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
    for name in ("index.md", "log.md"):
        if os.path.isfile(os.path.join(root, name)):
            pages.append(read_page(root, name))
    for folder in ("wiki",) + OVERLAY_DIRS:
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


def is_iso_date(value):
    return bool(_ISO_DATE.match(value or ""))
