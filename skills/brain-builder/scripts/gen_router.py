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

from brain_contract import (
    BUSINESS_KIND,
    DEFAULT_KIND,
    OVERLAY_DIRS,
    PERSONA_KIND,
    default_stance,
    read_page,
)

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
        return self.has_persona and self.answers_in_a_persons_voice

    @property
    def answers_in_a_persons_voice(self):
        """Whether this brain will answer *as somebody* — the stance decides.

        Deliberately not `has_persona`: the anti-caricature brake is mandatory
        (spec.md §4), and a `kind: persona` brain whose overlay has not been
        written yet still takes the persona stance and still speaks as them. A
        brake that vanishes with a missing folder is no brake. It is not
        `kind` either — a declared stance always wins, and a persona-kind brain
        that has explicitly opted into the advisor stance imitates nobody.
        """
        return self.stance == PERSONA_KIND

    @property
    def is_business(self):
        return self.kind == BUSINESS_KIND

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
    """The shared blocks every brain carries, plus the ones its kind adds.

    Per-kind sections are **additive**: a subject brain renders exactly the six
    shared blocks, and a persona or business brain renders those same blocks
    with its own slotted in beside them. Nothing a kind adds rewrites a shared
    rule, which is what keeps one committed reference router regenerable.
    """
    sections = [_header(meta), _navigation(), _stance(meta)]
    if meta.speaks_as_persona:
        sections.append(_persona_overlay(meta))
    if meta.answers_in_a_persons_voice:
        sections += [_anti_caricature(meta), _calibration(meta)]
    if meta.has_standing:
        sections.append(_standing_overlay())
    sections.append(_answering(meta))
    if meta.is_business:
        sections += [_freshness(), _confidentiality()]
    sections += [_citation(meta), _write_back(), _conflicts()]
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
        "- **`quarantine/` is never opened at all.** If it exists, it holds material the",
        "  rights stance refused to ingest — paywalled stubs kept only so the member can",
        "  see what was skipped. It is not this brain's knowledge and is never quoted.",
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
    if meta.is_business:
        lines += [
            "- **Outside the business, never inside it.** This brain holds one",
            "  organisation's own facts and you are not that organisation: \"you offer X\",",
            "  \"the business charges Y\" — **never \"we\"**. Saying \"we\" is how an answer stops",
            "  being an answer and becomes a commitment made on their behalf.",
        ]
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
        "- The overlay is **never cited**. It carries no facts, so it never appears in a",
        "  Sources block — cite the wiki page the claim itself came from.",
    ])


def _anti_caricature(meta):
    """Mandatory on every persona brain — a hallucination brake, not a style note.

    An imitated voice reaches for the loudest three traits and then invents the
    figures that fit the shape it has made. Written down, this block demonstrably
    killed invented statistics before they reached a page (spec.md §4).
    """
    return "\n".join([
        "## Anti-caricature",
        "",
        "This is a **hallucination brake before it is a style note**. An imitated voice",
        "reaches for the loudest traits and then invents the numbers that fit them.",
        "",
        "- **Never improvise a number.** A figure that is not on a wiki page does not get",
        "  said in {}'s voice — no rounding to what sounds right, no benchmark".format(meta.title),
        "  recalled from general knowledge and put in their mouth. A confident voice",
        "  attached to an invented figure is the worst thing this brain can do.",
        "- **Use their tics at the rate the corpus uses them**, which is far lower than an",
        "  impression of them. A catchphrase in every answer is caricature, not fidelity.",
        "- **Never extend their positions.** Where they have not covered something, they",
        "  have not covered it — say so in their register rather than generating the view",
        "  they would probably hold.",
        "- Where the corpus is **thin**, confidence drops with it. Their certainty is not",
        "  yours to perform.",
    ])


def _calibration(meta):
    """The persona kind's proof: one question whose answer is already known."""
    return "\n".join([
        "## Calibration",
        "",
        "- The check is one question whose **answer you already know** from the corpus —",
        "  `index.md`'s one-liners carry the real numbers, so a known answer is always to",
        "  hand. Both halves are checked at once: the fact lands, and it sounds like",
        "  {} at the length they would actually answer at.".format(meta.title),
        "- The question and the answer it should give are **written into `log.md`** at",
        "  build time, so the check is a fixed one rather than whatever comes to mind. Ask",
        "  it again after any write-back that touches the pages it runs through.",
        "- A voice miss is an overlay problem — too few exemplars, or exemplars with no",
        "  range. A fact miss is a thin page or a `## Known gaps` entry. They are fixed in",
        "  different places, so name which one missed.",
    ])


def _standing_overlay():
    return "\n".join([
        "## Standing overlay",
        "",
        "- `standing/` holds this brain's standing facts and policies. It is **unfenced**:",
        "  routed exactly like `wiki/` pages, and loaded whole when it is relevant.",
        "- Standing policies bind outward-facing work — see Conflicts below.",
    ])


def _answering(meta):
    """The shared answering rules.

    The fast-volatility rule is stated here for every kind that has no
    `## Freshness` block of its own — freshness frontmatter belongs to the
    business kind but is available to any brain (spec.md §2). A business brain
    gets the fuller treatment instead, and stating it in both places would leave
    the same rule in one router twice.
    """
    freshness = [] if meta.is_business else [
        "- Facts from pages marked `volatility: fast` are answered with their **as-of date",
        "  attached in the same breath** — the number stays exact, the date is the honesty.",
    ]
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
    ] + freshness)


def _freshness():
    """Business kind: the date is what keeps an exact number honest (spec.md §4)."""
    return "\n".join([
        "## Freshness",
        "",
        "- A fact from a page carrying `as_of` is answered **with its date attached in the",
        "  same breath** — the number stays exact, the date is the honesty. It is not a",
        "  hedge, and it does not soften the answer.",
        "- `volatility: fast` pages are the ones that rot — prices, rates, capacity,",
        "  current status. Attach the date to those without exception, and name the page's",
        "  `canonical:` source alongside it: that is where the live truth is confirmed today.",
        "- `slow` and `stable` facts are answered flat. The date is there if it is asked for.",
        "- When a `fast` fact's `as_of` is old enough that it has probably moved, say so in",
        "  a clause and point at `canonical:`. Never serve a stale number silently, and",
        "  never refuse to give the number at all — the member wants both halves.",
        "- **Write-back is routine here**, not exceptional: this is the kind that goes",
        "  stale. A price, status or process confirmed in conversation files back the same",
        "  day, with `as_of` set to that day.",
    ])


def _confidentiality():
    """Business kind: the material is the organisation's own (spec.md §4)."""
    return "\n".join([
        "## Confidentiality",
        "",
        "- This brain is **local-only**. Its material is the business's own: it is not",
        "  published, pasted, or summarised into anything that leaves this machine.",
        "- **One client's details never reach another client's documents**, and never",
        "  reach outward-facing drafts, **unasked**. Rates, terms, volumes and names are",
        "  what leak. So do aggregates: \"most clients pay around …\" is one client's rate",
        "  in a disguise when there are four of them.",
        "- Drafting anything a named client will read uses their page, the offers, and",
        "  standing policy. No other client's page is opened for it.",
        "- The rule is **unasked**, not *never*: a member who explicitly asks to compare",
        "  accounts gets the comparison. It simply never happens on the way to answering",
        "  something else.",
    ])


def _citation(meta):
    if meta.is_business:
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
    # `standing/` is routed like `wiki/`, so an answer can be grounded in it —
    # and a grounded answer with no sanctioned path form is an uncitable answer.
    standing = [
        "- `standing/` is routed like `wiki/`, so cite it the same way:",
        "  `standing/<page>.md`, or `{}/standing/<page>.md` when stacked.".format(meta.slug),
    ] if meta.has_standing else []
    return "\n".join([
        "## Citation",
        "",
    ] + weight + [
        "- Paths are brain-relative and name the file you would edit to fix an error:",
        "  `wiki/<page>.md`. Inline markers are permitted but minimal — citations are",
        "  asides, never the spine of an answer.",
        "- In stacked sessions, prefix every path with this brain's slug:",
        "  `{}/wiki/<page>.md`.".format(meta.slug),
    ] + standing + [
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
