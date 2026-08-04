#!/usr/bin/env python3
"""Generate a brain's `SKILL.md` router (spec.md §3).

    python3 gen_router.py <brain-dir> [--kind <kind>] [--root <path>]

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
                directory once attached. `--root` records a location other than
                the one the brain currently sits in — for a brain generated
                before it is moved into place, or a reference brain committed to
                a repo, whose real home is `~/brains/<slug>/`.

Metadata comes off the brain itself — `index.md` frontmatter (`slug`, `title`,
`domain`, `kind`, `stance`) — with the folder name as the fallback slug and
title. Overlays are never declared: `persona/` and `standing/` are detected on
disk. A declared `stance` always wins; where none is declared, a persona kind or
a `persona/` overlay implies the persona stance, and everything else is advisor.

Stdlib only.
"""
import os
import sys

from brain_contract import DEFAULT_KIND, OVERLAY_DIRS, default_stance, read_page

PERSONA_OVERLAY, STANDING_OVERLAY = OVERLAY_DIRS


class BrainMeta(object):
    """What the brain says about itself, as the router needs it."""

    def __init__(self, root, recorded_root, slug, title, domain, kind, stance, overlays):
        self.root = root                    # where the brain sits now
        self.recorded_root = recorded_root  # the root the router records
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
    def speaks_as_persona(self):
        """Voice files plus the stance to use them. Either alone is not a persona."""
        return self.has_persona and self.stance == "persona"

    @property
    def has_standing(self):
        return STANDING_OVERLAY in self.overlays


def read_brain_meta(root, kind=None, recorded_root=None):
    """Read a brain's own account of itself off `index.md` and its folders."""
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isfile(os.path.join(root, "index.md")):
        raise ValueError("{}: no index.md — not a brain, nothing to route".format(root))
    front = read_page(root, "index.md").frontmatter

    folder = os.path.basename(root)
    overlays = [name for name in OVERLAY_DIRS if os.path.isdir(os.path.join(root, name))]
    resolved_kind = kind or _text(front.get("kind")) or DEFAULT_KIND
    return BrainMeta(
        root=root,
        recorded_root=recorded_root or root,
        slug=_text(front.get("slug")) or folder,
        title=_text(front.get("title")) or folder,
        domain=_text(front.get("domain")),
        kind=resolved_kind,
        stance=_resolve_stance(_text(front.get("stance")), resolved_kind, overlays),
        overlays=overlays,
    )


def _resolve_stance(declared, kind, overlays):
    """A declared stance always wins — stances are extensible, not a cap of two."""
    return declared or default_stance(kind, overlays)


def _text(value):
    if isinstance(value, list):
        value = " ".join(str(part) for part in value)
    return str(value).strip() if value is not None else ""


def generate_router(root, kind=None, recorded_root=None):
    """Return the full text of the brain's `SKILL.md`."""
    return render_router(read_brain_meta(root, kind=kind, recorded_root=recorded_root))


def render_router(meta):
    """Render a router from metadata already read."""
    return _frontmatter(meta) + "\n" + "\n\n".join(_sections(meta)) + "\n"


def write_router(root, kind=None, recorded_root=None):
    """Write (or rewrite, in place) the brain's `SKILL.md`. Returns its path."""
    meta = read_brain_meta(root, kind=kind, recorded_root=recorded_root)
    path = os.path.join(meta.root, "SKILL.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_router(meta))
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
        "  brain_root: {}".format(meta.recorded_root),
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
    if meta.speaks_as_persona:
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
    ).format(title=meta.title, root=meta.recorded_root)


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
    if meta.speaks_as_persona:
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
        "- Load `persona/voice.md` and `persona/exemplars.md` **whole**, and never merge",
        "  them with facts pages: voice is not evidence, and evidence is not voice.",
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
        "- **Stay inside the page budget**: 2–3 wiki pages per question, per brain. If",
        "  three pages do not answer it, say what is missing rather than opening more.",
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
    positional, options = [], {"--kind": None, "--root": None}
    pending = iter(argv[1:])
    for arg in pending:
        name, _, inline = arg.partition("=")
        if name in options:
            value = inline if inline else next(pending, None)
            if not value:
                sys.stderr.write("gen_router.py: {} needs a value\n".format(name))
                return 2
            options[name] = value
        else:
            positional.append(arg)
    if len(positional) != 1:
        sys.stderr.write("usage: gen_router.py <brain-dir> [--kind <kind>] [--root <path>]\n")
        return 2
    try:
        path = write_router(positional[0], kind=options["--kind"],
                            recorded_root=options["--root"])
    except (ValueError, OSError) as failure:
        sys.stderr.write("gen_router.py: {}\n".format(failure))
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
