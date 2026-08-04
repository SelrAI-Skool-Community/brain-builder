# Prototype findings: one real brain, end to end

Migrated from planning ticket CORE-128 (resolved 2026-08-03). A throwaway persona brain was built end to end in the locked representation shape (SKILL.md router + index.md + raw/ + wiki/ + log.md, with a persona overlay) and used live. The brain itself stays local (see `docs/rights.md`); these are the findings.

## The build

30 hand-picked videos (from 510 found) → 21 MB VTT → 223,642 clean words → 54 wiki pages across 7 sections (~39K words, 5.7x compression) plus a persona overlay (voice.md + 30 verbatim exemplars). 8 parallel agents, ~30 min wall clock.

## Does it feel like an expert? Yes, and the win is fidelity, not helpfulness

Tested head to head against a deliberately strong brain-less control told to act as an expert on the same person. The control produced excellent generic consulting but was confidently wrong *about him*: it called a 6% monthly churn figure "middling" where the corpus shows the platform average is 20% and 6% is top-tier. Opposite advice. Same on margin. A model asked to channel someone without a brain invents plausible benchmarks and attributes them to them. That, plus checkable receipts on every claim, is the product.

Routing held: 17 files opened across 6 test questions, zero misroutes, no speculative reads. The causal factor: index one-liners that carry the actual numbers, not topic labels. Index generation is a first-class build step, not a byproduct.

## Three contract changes the prototype forced

1. **Answering rules are as load-bearing as navigation rules.** The first build routed perfectly and still felt wrong, because it narrated its own retrieval ("Loading it", "Read five pages") and framed answers as "here's what the brain says". Every generated brain needs both halves of the contract: how to find, and how to speak.
2. **Commit to a stance.** A brain either speaks as the person or it doesn't; the failure mode is hovering in between and relaying a third party at arm's length. The rule is "pick a stance and hold it", extensible, not a cap of two.
3. **Citation placement and weight are separate specifications.** De-emphasising citations without mandating a block made them vanish entirely. Settled shape: exactly one closing Sources block of brain-relative file paths, citations as asides, never the spine.

## Also validated

- **Persona/facts separation holds in practice.** The persona overlay correctly did not load on facts questions.
- **The anti-caricature section is a hallucination brake**, not a style note: it demonstrably killed two invented statistics before they reached a page. Mandatory in the overlay contract.
- **`## Known gaps` in index.md is what enables honest refusal.** The brain declined an out-of-corpus question where the control answered fluently from general knowledge. Trustworthy-but-bounded is the accepted trade.
- **voice.md needs a short-form register section** ("them at three paragraphs"); distilling only from long monologues leaks fidelity on compressed output.

## Pipeline requirements, now evidence-backed

- **Caption dedup is load-bearing:** YouTube rolling captions inflate word count ~3-4x in near-duplicates.
- **Corpus-level dedup above the file level:** the largest video was a compilation repeating another near-verbatim.
- **A number-verification pass:** ASR corrupts exactly the names and figures that matter (mangled surnames, "$4,600" for $46M); a misheard figure becomes a confidently cited wiki fact. Cross-check numbers against surrounding arithmetic.
- **Lint is required, empirically:** 191 internal links, 8 dangling (4.2%), all cross-section forward links written by parallel agents that couldn't see each other's output. Leftovers land in `## Known gaps`.
- **A shared taxonomy pass before parallel section agents**, or material lands in wrong or competing slices.
- **Per-page provenance context beyond citations:** a page must say what scale/context its numbers come from.
