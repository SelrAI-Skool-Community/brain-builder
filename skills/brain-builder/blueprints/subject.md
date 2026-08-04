---
kind: subject
summary: A wiki organised by concept, advisor stance, no overlays — the default shape for a body of knowledge about a topic.
stance: advisor
overlays: []
wiki_organised_by: concept
---

# Subject — blueprint

The default kind, and the one most brains want. A subject brain holds what is
known about a topic and answers as an expert who holds it: **advisor stance**,
Claude speaking as itself, no voice to imitate and no business to speak for.

This file is a **skeleton, not an example**. Nothing here gets copied into a
brain verbatim — read it, then build the shape it describes out of the material
actually ingested. If a section below does not fit the corpus, the corpus wins.

## When to suggest this shape

Suggest subject when the member describes a **topic** — a field, a craft, a
method, a body of research — rather than a person to sound like or a business to
speak for. Signals: "everything about X", "how X works", "what the experts say
about X", a folder of notes/papers/docs on one theme.

Suggest a different kind when the member wants the brain to **sound like
someone** (persona) or to hold **one organisation's own facts, prices and
policies** (business). Do not fold those in here — one blueprint per brain;
multi-kind behaviour is stacking at attach time, not merging at build time.

## Wiki taxonomy — organised by concept

Pages are **concepts, not sources**. The corpus is the input; the taxonomy is a
map of the ideas in it. A wiki with one page per document is an archive, not a
brain — it forces the router to guess which document held the answer.

Shape it like this:

- One page per concept a member would ask about by name. If two concepts are
  only ever discussed together, they are one page.
- Page names are the concept in the member's language, not the corpus's jargon —
  the router matches a question against these names.
- Depth over breadth: a page carrying the real numbers on one concept beats
  three pages restating each other. Aim for pages that answer a question fully;
  split when a page starts serving two unrelated questions.
- Cross-link concepts that constrain each other. A page nobody links to and that
  links to nothing is a page the router will never reach through.
- No overlays. `persona/` and `standing/` belong to other kinds; a subject brain
  that grows one has chosen the wrong blueprint.
- Interior structure is free: subfolders under `wiki/` are fine where a domain
  genuinely nests. Lint does not care, and neither should the shape.

## Page shape

Each wiki page carries OKF frontmatter and then answers its concept:

- `type:` — required on every page; the concept's category in this brain's own
  vocabulary (the contract only requires that it is present and not a reserved
  name).
- `title:` — the concept as a member would say it.
- `sources:` — the `raw/` files this page was distilled from. This is the chain
  back to source, which is why answers cite the wiki page rather than `raw/`.
- Optional freshness fields (`as_of`, `volatility`, `canonical`) where a fact
  genuinely goes stale. Most subject material is `stable` and needs none of it;
  do not decorate pages with fields that carry no information.

The body leads with the answer the page exists to give, then the detail that
supports it, then what it depends on. Numbers stay exact and keep their context
(the scale, the conditions, the units they were measured under) — a number
stripped of its context is the failure mode that makes a brain confidently
wrong.

## index.md

The map, and the only page loaded every session. Its one-liners are what routing
runs on, so each one carries **the page's actual numbers**, not a topic label. A
one-liner that would fit any page in the brain has told the router nothing.

`## Known gaps` is required and honest: what falls inside this brain's domain and
is not covered. This is the register that refusal fires from — a subject brain
answers out-of-domain questions normally, and only refuses when the question is
in-domain but uncovered.

## Calibration

Ask the brain one of the member's own intake questions the moment it is built.
The answer either lands with the corpus's real numbers or it does not, and that
is the only proof that matters. Where it misses, the miss is a Known gap or a
thin page — both are fixable, and both are worth knowing before the member finds
them.
