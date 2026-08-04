# Stacking verification at n=2

The stacking contract (spec.md §3) is the part of the router that only does
anything when a second brain is attached: slug-prefixed citation paths, a
per-brain page budget, one voice per session, and the conflict rule. A single
brain can carry all of it and prove none of it.

This record says what is now checked automatically, what the check is worth, and
what still needs a live session. Written alongside CORE-150, which shipped the
persona and business kinds.

## The pair

Two hand-authored reference brains, committed under `tests/fixtures/`, chosen so
that the two hardest kinds are the ones stacked:

| | `marlow-quist` | `rye-lane-bakery` |
|---|---|---|
| Kind | persona | business |
| Stance | persona — speaks as the person | advisor — speaks from outside the business |
| Overlay | `persona/` (`voice.md` + 12 exemplars) | `standing/` (trading policy) |
| Wiki | 3 concept pages | 4 pages by entity and process |
| Freshness | none — the material is stable | `as_of` on every page, two of them `fast` |

**Both are invented.** Marlow Quist is not a real person and Rye Lane Bakery is
not a real business. A persona fixture distilled from a real person's words, or a
business fixture built from a real organisation's paperwork, is exactly what the
rights stance forbids committing ([rights.md](../rights.md)) — so the corpora in
`raw/` were written for the purpose. They are shaped like real corpora (one
speaker verbatim across sessions; an issued rate card that contradicts a
superseded one) because the shape is the thing under test.

They also sit deliberately close together. Both are about bread, so a misrouted
question is a plausible mistake rather than an obvious one, and the brains
disagree on something real: Marlow's guidance says a higher-hydration loaf is
fine above 13 % protein flour, while the bakery's programme is three fixed shapes
with no bespoke supply and its trading policy declines own-label work outright.
Asked whether a cafe can have a wetter loaf, the two brains give opposite
answers, and the business one is supposed to win. That is the conflict rule's
test case rather than a hypothetical.

## What `tests/test_stacking.py` asserts

Static properties of the two committed brains and their generated routers:

- **Both are valid brains** — lint clean, no errors and no warnings.
- **Both routers are what the generator produces.** Regenerating either into a
  copy is byte-identical to what is committed, so a hand-edited router cannot
  survive in the repo.
- **Each declares itself distinctly.** The persona description names Marlow Quist
  and never the bakery; the business description names the bakery and never
  Marlow Quist. Both carry the start-at-index/never-glob clause in the
  description itself, where a session that globs before reading a router body
  will still meet it.
- **Kind sections land where they should and nowhere else.** Anti-caricature and
  calibration in the persona router only; freshness, confidentiality, the
  outside-the-business stance rule and the conditional Sources block in the
  business router only.
- **The shared stacking rules survive in both** — the per-brain page budget
  stated as per brain, one voice per session with the others as silent fact
  sources, and the conflict rule surfacing rather than silently resolving.
- **Citation paths are slug-prefixed per brain**: `marlow-quist/wiki/<page>.md`
  and `rye-lane-bakery/wiki/<page>.md`.
- **The overlays keep their different contracts.** `standing/` is linked from
  `index.md` because it is routed like wiki pages; `persona/` is not, because the
  router loads it whole.

## What that is worth, honestly

These are **document tests, not behaviour tests**. They prove the contract is
present, complete, per-kind, and regenerable. They cannot prove it is obeyed —
routing, voice fidelity and conflict handling are properties of a session, and
nothing in a unit test opens a file the way an agent does.

Two specific things are asserted only as text:

- **"Correct routing off frontmatter descriptions alone."** What is checked is
  that the descriptions are distinguishable and carry the never-glob clause. That
  they *do* route a real question to the right brain was measured in the
  prototype (CORE-141: n=2, zero misroutes, no orchestration layer) — on a
  different pair of brains from these.
- **"At most one persona driving voice."** Checked as a rule in both routers.
  Whether a business brain stays a silent fact source while a persona answers is
  a live-session property.

## What still needs a live session

Attach both, ask four questions, record what happened:

1. **A business fact.** "What does the wholesale sourdough cost?" — expect £3.10
   with `as of 2026-06-01` attached in the same breath, a Sources block (it
   carries a number), and Marlow's voice nowhere near it.
2. **A persona question.** "How should I think about hydration?" — expect first
   person, the 68 % beginner ceiling, no invented figures, and no bakery pages
   opened.
3. **A crossing question.** "A cafe wants a wetter, more open loaf — can we do
   it?" — expect the bakery's three-shapes-only programme and its no-bespoke
   trading policy to outrank Marlow's "yes, above 13 % protein", with the
   disagreement stated in the answer rather than quietly resolved.
4. **A confidentiality probe.** "What do our other accounts pay?" — expect the
   one-client-per-answer rule to hold without being asked for.

Until that is run and written up here, n=2 stacking for these two kinds is
**verified by construction and inherited from the prototype**, not re-measured.
