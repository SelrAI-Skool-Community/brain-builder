#!/usr/bin/env python3
"""Generate a brain's `SKILL.md` router (spec.md §3).

    python3 gen_router.py <brain-dir> [--kind <kind>]

The router is the brain's entire consumption interface: no query skill, no
wrapper, no config file. Its frontmatter description fires it from natural
language and carries the start-at-index/never-glob clause itself, because two
stacked-test sessions globbed before the router body was ever in context. Its
body carries all four rule blocks — navigation, stance, answering, citation —
plus write-back and the conflict rule.

Two properties the rest of the kit depends on:

  regenerable   Re-running rewrites `SKILL.md` in place, byte for byte. There
                are no timestamps in the output, so a no-op regeneration is a
                no-op diff. Never hand-edit a router; regenerate it.
  self-rooted   The brain's absolute root is recorded in the frontmatter
                metadata and in the body, so the router works from any
                directory once attached.

Metadata comes off the brain itself — `index.md` frontmatter (`slug`, `title`,
`domain`, `kind`, `stance`) — with the folder name as the fallback slug and
title. Overlays are never declared: `persona/` and `standing/` are detected on
disk, and the persona stance follows the overlay, not the label.

Stdlib only.
"""
import os
import sys

from brain_contract import OVERLAY_DIRS, parse_frontmatter

DEFAULT_KIND = "subject"
PERSONA_OVERLAY = "persona"
STANDING_OVERLAY = "standing"


class BrainMeta(object):
    """What the brain says about itself, as the router needs it."""

    def __init__(self, root, slug, title, domain, kind, stance, overlays):
        self.root = root
        self.slug = slug
        self.title = title
        self.domain = domain
        self.kind = kind
        self.stance = stance
        self.overlays = overlays

    @property
    def has_persona(self):
        return PERSONA_OVERLAY in self.overlays

    @property
    def has_standing(self):
        return STANDING_OVERLAY in self.overlays


def read_brain_meta(root, kind=None):
    """Read a brain's own account of itself off `index.md` and its folders."""
    root = os.path.abspath(os.path.expanduser(root))
    index = os.path.join(root, "index.md")
    if not os.path.isfile(index):
        raise ValueError("{}: no index.md — not a brain, nothing to route".format(root))
    with open(index, "r", encoding="utf-8") as handle:
        front, _, _ = parse_frontmatter(handle.read())

    folder = os.path.basename(root)
    slug = _text(front.get("slug")) or folder
    overlays = [name for name in OVERLAY_DIRS if os.path.isdir(os.path.join(root, name))]
    resolved_kind = kind or _text(front.get("kind")) or DEFAULT_KIND
    stance = _text(front.get("stance")) or ("persona" if PERSONA_OVERLAY in overlays else "advisor")
    return BrainMeta(
        root=root,
        slug=slug,
        title=_text(front.get("title")) or folder,
        domain=_text(front.get("domain")),
        kind=resolved_kind,
        stance="persona" if PERSONA_OVERLAY in overlays else stance,
        overlays=overlays,
    )


def _text(value):
    if isinstance(value, list):
        value = " ".join(str(part) for part in value)
    return str(value).strip() if value is not None else ""


def generate_router(root, kind=None):
    """Return the full text of the brain's `SKILL.md`."""
    meta = read_brain_meta(root, kind=kind)
    return _frontmatter(meta) + "\n" + "\n\n".join(_sections(meta)) + "\n"


def write_router(root, kind=None):
    """Write (or rewrite, in place) the brain's `SKILL.md`. Returns its path."""
    meta = read_brain_meta(root, kind=kind)
    path = os.path.join(meta.root, "SKILL.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(generate_router(meta.root, kind=kind))
    return path


# --- frontmatter -----------------------------------------------------------

def _frontmatter(meta):
    domain = meta.domain or "the material in this brain"
    description = (
        "{title} — {domain} Use when the question is about {title}, or when an answer "
        "needs this brain's facts, numbers, or guidance. Start at index.md and follow "
        "its links; never glob or bulk-load the brain."
    ).format(title=meta.title, domain=_sentence(domain))
    lines = [
        "---",
        "name: {}".format(meta.slug),
        'description: "{}"'.format(description.replace('"', "'")),
        "metadata:",
        "  type: brain-router",
        "  kind: {}".format(meta.kind),
        "  stance: {}".format(meta.stance),
        "  brain_root: {}".format(meta.root),
    ]
    if meta.overlays:
        lines.append("  overlays: [{}]".format(", ".join(meta.overlays)))
    lines.append("---")
    return "\n".join(lines) + "\n"


def _sentence(text):
    return text if text.endswith((".", "!", "?")) else text + "."


# --- body ------------------------------------------------------------------

def _sections(meta):
    sections = [_header(meta), _navigation(), _stance(meta)]
    if meta.has_persona:
        sections.append(_persona_overlay(meta))
    if meta.has_standing:
        sections.append(_standing_overlay())
    sections += [_answering(), _citation(meta), _write_back(), _conflicts()]
    return sections


def _header(meta):
    return (
        "# {title} — brain router\n\n"
        "This file is the brain's entire interface — no query skill, no wrapper, no\n"
        "config file. It is generated: regenerate it rather than editing it by hand.\n\n"
        "- **Brain root**: `{root}`\n"
        "- **Regenerate**: `python3 gen_router.py {root}`"
    ).format(title=meta.title, root=meta.root)


def _navigation():
    return "\n".join([
        "## Navigation",
        "",
        "- Start at `index.md` and follow its links to the two or three pages that answer",
        "  the question. Never glob, never bulk-load a folder, never read the tree to see",
        "  what is in it. Its one-liners carry the real numbers — route on those.",
        "- `index.md` loads **once per session**. After that, direct routing is allowed:",
        "  go straight to the page you already know you need.",
        "- Budget: **2–3 wiki pages per question, per brain**. When brains are stacked the",
        "  budget is per brain, not shared between them.",
        "- `wiki/` has its own interior taxonomy. It is this brain's, not a fixed one.",
        "- **`raw/` is fenced**: immutable source material, excluded from the index, opened",
        "  only for a verbatim quote or an explicit question about provenance.",
    ])


def _stance(meta):
    lines = [
        "## Stance",
        "",
        "- Commit to a stance and hold it — the failure mode is hovering between two.",
        "- **Advisor stance is the default**: answer as yourself, an expert who holds this",
        "  material. This brain's declared stance is **{}**.".format(meta.stance),
    ]
    if meta.has_persona:
        lines.append("- This brain declares a persona. See the persona overlay below; it changes")
        lines.append("  the voice, never the facts.")
    lines += [
        "- Stances are **extensible**. A brain may declare one this router has never heard",
        "  of; that is not an error, and this is not a list of two.",
        "- **No middleman.** Never relay a named third party at arm's length. \"Here's what",
        "  the brain says\", \"according to the brain\", \"the brain suggests\" are **banned** in",
        "  every stance — you hold the knowledge, so speak from it. The one sanctioned",
        "  exception is flagging a corpus boundary, and it costs one sentence.",
        "- **One voice per session.** When brains are stacked, at most one persona drives",
        "  the voice; while it does, every other attached brain is a silent fact source.",
        "  Non-persona stances stay advisor-compatible.",
    ]
    return "\n".join(lines)


def _persona_overlay(meta):
    return "\n".join([
        "## Persona overlay",
        "",
        "- **Speak as {}** — first person, their voice, never a report about them.".format(meta.title),
        "- Load `persona/voice.md` and `persona/exemplars.md` whole, and never merge them",
        "  with facts pages: voice is not evidence and evidence is not voice.",
        "- The anti-caricature section of `persona/voice.md` is a hallucination brake, not a",
        "  style note. Honour it — inventing a statistic in the right voice is still",
        "  inventing a statistic.",
        "- The overlay does not load for pure facts questions.",
    ])


def _standing_overlay():
    return "\n".join([
        "## Standing overlay",
        "",
        "- `standing/` holds this brain's standing facts and policies. It is **unfenced**:",
        "  routed exactly like `wiki/` pages, and loaded whole when it is relevant.",
        "- Standing policies bind outward-facing work — see Conflicts below.",
    ])


def _answering():
    return "\n".join([
        "## Answering",
        "",
        "- **Lead with the answer.** The first sentence answers the question.",
        "- **Never narrate retrieval.** No \"Loading…\", no \"Reading the index\", no \"I found",
        "  five pages\". The work is invisible; the answer is the output.",
        "- Second person, your own voice, flat certainty on this brain's own facts.",
        "- **In-domain gaps**: `index.md`'s `## Known gaps` section is the register. Refusal",
        "  fires **only** when the question is inside the domain but uncovered — say so",
        "  plainly, in a sentence, and offer what the brain does cover nearby.",
        "- **Out-of-domain questions are answered normally** from general knowledge, with",
        "  **no disclaimer** and no Sources block. Not every question in a session is a",
        "  question for this brain.",
        "- Facts from pages marked `volatility: fast` are answered with their **as-of date",
        "  attached in the same breath** — the number stays exact, the date is the honesty.",
    ])


def _citation(meta):
    if meta.kind == "business":
        weight = [
            "- **Exactly one closing `Sources` block**, and for this business brain it is",
            "  conditional: only on answers carrying numbers, prices, dates, or commitments,",
            "  annotated `(as of …; canonical …)`. Other answers carry none.",
        ]
    else:
        weight = [
            "- **Exactly one closing `Sources` block.** Every answer grounded in this brain",
            "  ends with one — never two, never scattered through the prose.",
        ]
    return "\n".join([
        "## Citation",
        "",
    ] + weight + [
        "- Paths are brain-relative and name the file you would edit to fix an error:",
        "  `wiki/<page>.md`. Inline markers are permitted but minimal — citations are",
        "  asides, never the spine of an answer.",
        "- In stacked sessions, prefix every path with this brain's slug:",
        "  `{}/wiki/<page>.md`.".format(meta.slug),
        "- **Never cite `raw/`** except when quoting it verbatim. A wiki page's frontmatter",
        "  is the chain back to source.",
        "- Out-of-domain answers carry no Sources block at all.",
        "- Pages written back from a conversation are marked **derived-from-conversation**",
        "  and cited as such, so a Sources block never implies grounding that does not",
        "  exist.",
    ])


def _write_back():
    return "\n".join([
        "## Write-back",
        "",
        "- A good answer files back into `wiki/` as a new page **during the conversation**.",
        "  **No staging**, **no approval gate**, no batch review at the end.",
        "- **Announce every write in-line**, in a clause: \"Filed that as `wiki/<page>.md`.\"",
        "- Append every write to `log.md`: the date, the page, and the question it came from.",
        "- Written-back pages carry `derived-from-conversation: true` in their frontmatter",
        "  alongside the usual OKF `type`, so citations stay honest.",
        "- **Undo is git.** Nothing else guards the write, so nothing else needs to.",
    ])


def _conflicts():
    return "\n".join([
        "## Conflicts",
        "",
        "- A business brain's facts and standing policies **outrank** subject-brain guidance",
        "  for outward-facing work — pricing, claims, commitments, anything a client sees.",
        "- **Surface every conflict; never silently resolve one.** State both positions, say",
        "  which wins and why, then carry on with the answer.",
    ])


# --- cli -------------------------------------------------------------------

def main(argv):
    positional, kind = [], None
    pending = iter(argv[1:])
    for arg in pending:
        if arg == "--kind":
            kind = next(pending, None)
            if kind is None:
                sys.stderr.write("gen_router.py: --kind needs a value\n")
                return 2
        elif arg.startswith("--kind="):
            kind = arg.split("=", 1)[1]
        else:
            positional.append(arg)
    if len(positional) != 1:
        sys.stderr.write("usage: gen_router.py <brain-dir> [--kind <kind>]\n")
        return 2
    try:
        path = write_router(positional[0], kind=kind)
    except (ValueError, OSError) as failure:
        sys.stderr.write("gen_router.py: {}\n".format(failure))
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
