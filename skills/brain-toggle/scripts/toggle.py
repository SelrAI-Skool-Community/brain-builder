#!/usr/bin/env python3
"""Attach and detach brains from the harnesses on this machine (spec.md §7).

    python3 toggle.py <command> [options]      # no arguments prints the usage

Two mechanical arms, and nothing else:

1. **Symlink** a brain folder into a harness's skills directory. The router's
   description is then the whole idle cost, and no restart is needed.
2. **Pointer block** — a delimited, reversible `<!-- brain: slug -->` block
   appended to an instruction file, for harnesses that read one instead of a
   skills directory. Brain *content* never goes into an instruction file:
   those inject whole, every turn.

Scoping: global is the default, project is the opt-in second mode. Semantics
are additive — skills directories load together, so a project attachment adds
to the globals rather than shadowing them.

Stdlib only, on purpose: the kit ships to members with zero infrastructure.
"""
import collections
import difflib
import os
import re
import sys

#: The mandatory minimum for a folder to be a brain (spec.md §2). Deliberately
#: restated rather than imported: a member can install brain-toggle alone. For
#: the full check, run the builder's `lint.py <brain-dir>` before attaching.
BRAIN_MINIMUM = ("SKILL.md", "index.md", "wiki")


class Harness(object):
    """One harness: where its skills directory lives, per scope."""

    def __init__(self, name, home_dir, project_dir):
        self.name = name
        self.home_dir = home_dir
        self.project_dir = project_dir


HARNESSES = {
    # Claude Code and the Claude Agent SDK read the same two directories.
    "claude-code": Harness("claude-code", ".claude/skills", ".claude/skills"),
    "codex": Harness("codex", ".codex/skills", ".codex/skills"),
}

SCOPES = ("global", "project")


class ToggleError(Exception):
    """Anything the member has to decide or fix before the operation can run."""


class NeedsConsent(ToggleError):
    """The diff has been shown and the member has not said yes yet.

    Exit 3, like `AttachedElsewhere`: not a failure, a decision. The pointer arm
    writes into a file the member authored, so the first block into one is shown
    before it is written (spec.md §7).
    """


class AttachedElsewhere(ToggleError):
    """The brain is already attached somewhere else — move it or leave it.

    Raised instead of quietly creating a second router for the same brain.
    """

    def __init__(self, slug, link):
        super(AttachedElsewhere, self).__init__(
            "{} is already attached at {} — move it there, or keep both on "
            "purpose".format(slug, link))
        self.slug = slug
        self.link = link


#: What an attach did: `action` is one of linked / already-attached / moved.
Attached = collections.namedtuple(
    "Attached", "slug link target action moved_from warnings")

#: One link found in a skills directory.
Attachment = collections.namedtuple("Attachment", "slug link target dangling")


# --- where a brain gets linked ---------------------------------------------

def harness(name):
    try:
        return HARNESSES[name]
    except KeyError:
        raise ToggleError("unknown harness {!r} — known: {}".format(
            name, ", ".join(sorted(HARNESSES))))


def project_root(cwd=None):
    """The git root containing `cwd`, else `cwd` itself.

    `.git` is a directory in a normal checkout and a file in a worktree; both
    mark the root.
    """
    path = os.path.abspath(cwd or os.getcwd())
    probe = path
    while True:
        if os.path.exists(os.path.join(probe, ".git")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return path
        probe = parent


def skills_dir(name, scope="global", cwd=None, home=None):
    """The absolute skills directory for `name` at `scope`.

    This is the path the skill states to the member before linking anything.
    """
    found = harness(name)
    if scope == "global":
        base = os.path.abspath(home or os.path.expanduser("~"))
        return os.path.join(base, *found.home_dir.split("/"))
    if scope == "project":
        return os.path.join(project_root(cwd), *found.project_dir.split("/"))
    raise ToggleError("unknown scope {!r} — known: {}".format(scope, ", ".join(SCOPES)))


# --- the symlink arm -------------------------------------------------------

def check_brain(path):
    """Raise unless `path` holds the mandatory minimum of a brain."""
    if not os.path.isdir(path):
        raise ToggleError("no such brain folder: {}".format(path))
    missing = [name for name in BRAIN_MINIMUM
               if not os.path.exists(os.path.join(path, name))]
    if missing:
        raise ToggleError("{} is not a brain — missing {}".format(
            path, ", ".join(missing)))


def slug_of(path):
    """A brain's slug is its folder name."""
    return os.path.basename(os.path.abspath(path))


def attach(brain, target, elsewhere=(), move=False):
    """Link `brain` into the `target` skills directory, and report what it took.

    `elsewhere` names the other skills directories of the *same harness* — the
    ones that would load alongside `target` and give the member two copies of
    this brain's router. An attachment found there is a decision, so it raises
    `AttachedElsewhere` unless `move` is set, in which case it is detached
    first. A link of the same name pointing at some *other* brain is not this
    brain's attachment and is never touched.
    """
    brain = os.path.abspath(brain)
    check_brain(brain)
    slug = slug_of(brain)
    link = os.path.join(os.path.abspath(target), slug)

    moved_from = None
    for other in elsewhere:
        existing = os.path.join(os.path.abspath(other), slug)
        if existing == link or not _links_to(existing, brain):
            continue
        if not move:
            raise AttachedElsewhere(slug, existing)
        detach(slug, other)
        moved_from = existing

    return Attached(slug=slug, link=link, target=brain, action=_link(brain, link),
                    moved_from=moved_from, warnings=stale_router_warnings(brain))


def _links_to(link, brain):
    """Whether `link` is a symlink standing for this exact brain."""
    return os.path.islink(link) and os.path.realpath(link) == os.path.realpath(brain)


def _link(brain, link):
    if os.path.islink(link):
        if _links_to(link, brain):
            return "already-attached"
        os.remove(link)
    elif os.path.exists(link):
        raise ToggleError(
            "{} exists and is not a symlink — something else put it there; "
            "move it aside yourself".format(link))
    os.makedirs(os.path.dirname(link), exist_ok=True)
    os.symlink(brain, link)
    return "linked"


def detach(slug, target):
    """Remove the brain's link from the `target` skills directory.

    Returns an `Attachment` describing what was unlinked, or None if there was
    nothing to unlink. In a skills directory the link's *name* is the brain's
    identity, so the name is what detach goes by — the target it pointed at is
    reported back so the member can see what came off.

    Only ever removes a symlink: a real directory belongs to someone else, and
    is reported rather than deleted.
    """
    link = os.path.join(os.path.abspath(target), slug)
    if os.path.islink(link):
        pointed_at = os.path.realpath(link)
        os.remove(link)
        return Attachment(slug=slug, link=link, target=pointed_at,
                          dangling=not os.path.isdir(pointed_at))
    if os.path.exists(link):
        raise ToggleError(
            "{} is a real directory, not a brain link — refusing to remove "
            "it".format(link))
    return None


def attachments(target):
    """Every brain link in the `target` skills directory, in slug order.

    Real directories are the member's own skills, and are left out.
    """
    base = os.path.abspath(target)
    if not os.path.isdir(base):
        return []
    found = []
    for name in sorted(os.listdir(base)):
        link = os.path.join(base, name)
        if not os.path.islink(link):
            continue
        target = os.path.realpath(link)
        found.append(Attachment(slug=name, link=link, target=target,
                                dangling=not os.path.isdir(target)))
    return found


_RECORDED_ROOT = re.compile(r"^\s*brain_root:\s*(.+?)\s*$", re.MULTILINE)


def recorded_root(brain):
    """The root the brain's router records, or None if it records none."""
    path = os.path.join(brain, "SKILL.md")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            head = handle.read(4096)
    except OSError:
        return None
    match = _RECORDED_ROOT.search(head)
    return match.group(1) if match else None


def stale_router_warnings(brain):
    """Warn when the router points somewhere the brain no longer is.

    Attaching does not move a brain, but a member might have; the router then
    sends the agent to a path that is gone. The builder regenerates it.
    """
    recorded = recorded_root(brain)
    if not recorded:
        return []
    actual = os.path.realpath(brain)
    if os.path.realpath(os.path.expanduser(recorded)) == actual:
        return []
    return ["the router records brain_root {} but the brain is at {} — "
            "regenerate it: python3 gen_router.py {} --root {}".format(
                recorded, actual, actual, actual)]


# --- the pointer arm -------------------------------------------------------

POINTER_OPEN = "<!-- brain: {} -->"
POINTER_CLOSE = "<!-- /brain: {} -->"


def render_pointer(slug, brain):
    """The block that goes in an instruction file: a pointer, never content.

    Instruction files inject whole on every turn, so the block stays at three
    lines — where the brain is, and where to start reading it.
    """
    return "\n".join([
        POINTER_OPEN.format(slug),
        "The {} brain is at {}. Start at its index.md and follow the links; "
        "never bulk-load it.".format(slug, os.path.realpath(brain)),
        POINTER_CLOSE.format(slug),
    ])


def read_text(path):
    """A file's contents, or "" when it does not exist yet.

    Only a missing file reads as empty. Any other error — unreadable, a
    directory — must propagate: treating it as empty would append the block to
    nothing and overwrite what the member wrote.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return ""


def pointer_text(current, slug, brain):
    """What `current` becomes once the block for `slug` is right.

    Member-authored text is never reformatted: an existing block is replaced
    between its own delimiters, and a new one is appended after everything
    else. A file with no final newline gains one — a line cannot be appended
    to a file that does not end.
    """
    block = render_pointer(slug, brain)
    lines = current.split("\n")
    span = _pointer_span(lines, slug)
    if span:
        start, end = span
        return "\n".join(lines[:start] + block.split("\n") + lines[end + 1:])
    if not current:
        return block + "\n"
    prefix = current if current.endswith("\n") else current + "\n"
    return prefix + "\n" + block + "\n"


def _pointer_span(lines, slug):
    """Line indices of the block for `slug`, or None."""
    opener, closer = POINTER_OPEN.format(slug), POINTER_CLOSE.format(slug)
    try:
        start = lines.index(opener)
        end = lines.index(closer, start)
    except ValueError:
        return None
    return start, end


def apply_pointer(path, slug, brain):
    """Write the block for `slug` into `path`. Returns what it did."""
    check_brain(brain)
    current = read_text(path)
    wanted = pointer_text(current, slug, brain)
    if wanted == current:
        return "unchanged"
    action = "updated" if _pointer_span(current.split("\n"), slug) else "added"
    _write_text(path, wanted)
    return action


def remove_pointer(path, slug):
    """Take the block for `slug` back out. Returns whether there was one.

    Removal is exact: the block, plus the one blank line that separated it
    from the member's own text, and nothing else. A file that existed only
    because the block was added to it is removed rather than left behind at
    zero bytes — reversible means the harness sees what it saw before.
    """
    current = read_text(path)
    lines = current.split("\n")
    span = _pointer_span(lines, slug)
    if not span:
        return False
    start, end = span
    if start > 0 and lines[start - 1] == "":
        start -= 1
    remaining = "\n".join(lines[:start] + lines[end + 1:])
    if not remaining.strip():
        os.remove(path)
        return True
    _write_text(path, remaining)
    return True


def pointer_diff(path, slug, brain):
    """A unified diff of what applying the block would do. Writes nothing."""
    current = read_text(path)
    wanted = pointer_text(current, slug, brain)
    if wanted == current:
        return ""
    name = os.path.basename(path)
    return "".join(difflib.unified_diff(
        current.splitlines(True), wanted.splitlines(True),
        fromfile=name, tofile="{} (with {} pointer)".format(name, slug)))


def _write_text(path, text):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


# --- cli -------------------------------------------------------------------

USAGE = """usage: toggle.py <command> [options]

  attach <brain-dir>   link a brain into a harness  [--move to relocate it]
  detach <slug>        remove that link
  list                 what is attached, and where
  resolve              print the skills directory an attach would use
  pointer-add <file> <brain-dir>     append the pointer block  [--yes past the first-use diff]
  pointer-remove <file> <slug>       take it back out
  pointer-diff <file> <brain-dir>    show the change without making it

options: --harness {harnesses}  --scope {scopes}
         --skills-dir DIR (an unlisted harness; overrides both)  --cwd DIR  --home DIR

exit: 0 done  1 failed  2 usage  3 needs a decision from the member
""".format(harnesses="|".join(sorted(HARNESSES)), scopes="|".join(SCOPES))

_FLAGS = ("--harness", "--scope", "--cwd", "--home", "--skills-dir")


def _parse(argv):
    # The same shape as the builder scripts' hand-rolled parsers. Kept separate
    # rather than shared: brain-toggle installs on its own, without the builder.
    positional = []
    options = {"--harness": "claude-code", "--scope": "global", "--cwd": None,
               "--home": None, "--skills-dir": None, "--move": False, "--yes": False}
    pending = iter(argv)
    for arg in pending:
        name, _, inline = arg.partition("=")
        if name in ("--move", "--yes"):
            options[name] = True
        elif name in _FLAGS:
            value = inline if inline else next(pending, None)
            if not value:
                raise ToggleError("{} needs a value".format(name))
            options[name] = value
        elif arg.startswith("--"):
            raise ToggleError("unknown option {}".format(arg))
        else:
            positional.append(arg)
    return positional, options


def _target_dir(options, scope=None):
    if options["--skills-dir"]:
        return os.path.abspath(options["--skills-dir"])
    return skills_dir(options["--harness"], scope or options["--scope"],
                      cwd=options["--cwd"], home=options["--home"])


def _sibling_scopes(options):
    """The other skills directories that would load alongside the target.

    Only the *same* harness's other scopes: a harness loads its global and
    project directories together, so a brain in both gives that harness two
    routers. A different harness is a different agent and never loads both, so
    attaching the same brain to Claude Code and to Codex is not a duplicate.

    `--skills-dir` names a directory belonging to a harness this script does
    not know, so its sibling scopes cannot be worked out; nothing is checked.
    """
    if options["--skills-dir"]:
        return []
    return [skills_dir(options["--harness"], scope, cwd=options["--cwd"],
                       home=options["--home"])
            for scope in SCOPES if scope != options["--scope"]]


def _cmd_resolve(positional, options):
    print(_target_dir(options))
    return 0


def _cmd_attach(positional, options):
    if len(positional) != 1:
        raise ToggleError("attach takes one brain directory")
    target = _target_dir(options)
    print("target: {}".format(target))
    result = attach(positional[0], target, elsewhere=_sibling_scopes(options),
                    move=options["--move"])
    if result.moved_from:
        print("moved {} from {} to {}".format(result.slug, result.moved_from, result.link))
    elif result.action == "already-attached":
        print("{} was already attached at {}".format(result.slug, result.link))
    else:
        print("attached {} -> {}".format(result.link, result.target))
    for warning in result.warnings:
        print("warning: {}".format(warning))
    return 0


def _cmd_detach(positional, options):
    if len(positional) != 1:
        raise ToggleError("detach takes one slug")
    slug = positional[0]
    removed = detach(slug, _target_dir(options))
    print("detached {} (was -> {})".format(removed.link, removed.target) if removed
          else "{} is not attached there".format(slug))
    return 0


def _cmd_list(positional, options):
    """What is attached, and where. Not an inventory of installed brains."""
    for name in sorted(HARNESSES):
        for scope in SCOPES:
            directory = skills_dir(name, scope, cwd=options["--cwd"],
                                   home=options["--home"])
            print("scanned {} {} {}".format(name, scope, directory))
            for item in attachments(directory):
                print("  {} [{} {}] -> {}{}".format(
                    item.slug, name, scope, item.target,
                    "  (BROKEN: target is gone)" if item.dangling else ""))
    return 0


def _cmd_pointer_add(positional, options):
    """Append the block — showing the diff first, the first time (spec.md §7).

    The instruction file is the member's own, injected whole on every turn, and
    the first write into one is the write they have not seen before. So the
    first use prints the diff and stops at exit 3, the same "needs a decision"
    code an ambiguous attach uses; `--yes` is the decision. Updating a block
    that is already there, or a re-run that changes nothing, is silent.
    """
    if len(positional) != 2:
        raise ToggleError("pointer-add takes an instruction file and a brain directory")
    path, brain = positional
    slug = slug_of(brain)
    if not options["--yes"] and not _pointer_span(read_text(path).split("\n"), slug):
        check_brain(brain)
        print(pointer_diff(path, slug, brain))
        raise NeedsConsent(
            "that is the first {} block {} would get — rerun with --yes to write it"
            .format(slug, path))
    print("{} pointer block for {} in {}".format(
        apply_pointer(path, slug, brain), slug, path))
    return 0


def _cmd_pointer_remove(positional, options):
    if len(positional) != 2:
        raise ToggleError("pointer-remove takes an instruction file and a slug")
    path, slug = positional
    print("removed pointer block for {} from {}".format(slug, path) if
          remove_pointer(path, slug) else "no {} pointer block in {}".format(slug, path))
    return 0


def _cmd_pointer_diff(positional, options):
    if len(positional) != 2:
        raise ToggleError("pointer-diff takes an instruction file and a brain directory")
    path, brain = positional
    diff = pointer_diff(path, slug_of(brain), brain)
    print(diff if diff else "no change: the pointer block is already correct")
    return 0


COMMANDS = {
    "attach": _cmd_attach,
    "detach": _cmd_detach,
    "list": _cmd_list,
    "resolve": _cmd_resolve,
    "pointer-add": _cmd_pointer_add,
    "pointer-remove": _cmd_pointer_remove,
    "pointer-diff": _cmd_pointer_diff,
}


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(USAGE)
        return 2
    if argv[1] in ("-h", "--help", "help"):
        sys.stdout.write(USAGE)
        return 0
    command = COMMANDS.get(argv[1])
    if command is None:
        sys.stderr.write("toggle.py: unknown command {!r}\n\n".format(argv[1]))
        sys.stderr.write(USAGE)
        return 2
    try:
        positional, options = _parse(argv[2:])
        return command(positional, options)
    except AttachedElsewhere as decision:
        sys.stderr.write(
            "toggle.py: {}\nrerun with --move to relocate it, or leave it "
            "global\n".format(decision))
        return 3
    except NeedsConsent as decision:
        sys.stderr.write("toggle.py: {}\n".format(decision))
        return 3
    except ToggleError as failure:
        sys.stderr.write("toggle.py: {}\n".format(failure))
        return 1
    except OSError as failure:
        sys.stderr.write("toggle.py: {}\n".format(failure))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
