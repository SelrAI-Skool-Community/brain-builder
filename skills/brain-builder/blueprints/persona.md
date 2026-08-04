---
kind: persona
summary: A subject wiki with a voice on top — one composite shape, where concept pages hold what the person knows and a persona/ overlay holds how they say it.
stance: persona
overlays: [persona]
wiki_organised_by: concept
---

# Persona — blueprint

A brain that **speaks as the person**. This is the only stance-changing kind:
everywhere else Claude answers as itself, and here it answers in the first
person, as them.

Persona is **one composite shape, never two brains** — a subject core with a
voice on top. The core is an ordinary concept wiki holding what the person
actually knows, built exactly as the subject blueprint describes; the `persona/`
overlay holds how they say it. Both halves are required. A voice with no
knowledge behind it invents the knowledge, which is the failure this shape
exists to prevent.

This file is a **skeleton, not an example**. Nothing here gets copied into a
brain verbatim — read it, then build the shape it describes out of the material
actually ingested. If a section below does not fit the corpus, the corpus wins.

## When to suggest this shape

Suggest persona when the member wants the brain to **sound like someone** — a
named person whose talks, writing, interviews or podcasts make up the corpus.
Signals: "answer as X", "what would X say", "I want to think like X", a corpus
that is one person's own output rather than a literature on a topic.

Suggest subject instead when the member wants what is known about a field and
does not care who says it, and business when they want one organisation's own
facts, prices and policies. Do not fold those in here — one blueprint per brain;
multi-kind behaviour is stacking at attach time, not merging at build time.

The corpus has to be **the person's own words**. Articles *about* someone, or a
biography, build a subject brain about them — the voice half has nothing to
distil from, and a voice distilled from other people's paraphrase is a
caricature with citations.

## The subject core — wiki organised by concept

Build `wiki/` the way the subject blueprint describes: pages are **concepts, not
sources**, named in the member's language, carrying the real numbers with their
context, cross-linked where concepts constrain each other.

Two things the persona kind adds to that:

- **The wiki is facts, not voice.** Their positions, frameworks, numbers and
  worked reasoning belong on pages. How they phrase things does not; that is the
  overlay's job, and duplicating it into pages is how facts pages start
  performing.
- **Keep their disagreements.** A person who changed their mind, or who holds a
  position most of their field does not, is exactly what the brain is for. Record
  the position and when it shifted rather than smoothing it into consensus.

## The `persona/` overlay

Two files, and the split between them is load-bearing:

`persona/voice.md` — a **thin list of observable rules**, not an essay about
them. Each line is something a reader could check against a transcript: sentence
length, how they open, what they do with a question they think is the wrong
question, the words they reach for, the words they never use, how they handle
numbers, where the humour sits. Include a **short-form register** section — how
they sound at three paragraphs, or one — because a voice distilled only from long
monologues leaks fidelity the moment the answer has to be short. If a rule cannot
be pointed at in the corpus, it is a guess and it comes out.

`persona/exemplars.md` — **10–20 verbatim excerpts**, quoted exactly, each with
its source. Chosen for **range**, not for being the best passages: long
explanation, short answer, a disagreement, a story, a correction, a throwaway
line. The exemplars do the heavy lifting on fidelity — `voice.md` names the
rules, the exemplars are the evidence, and the model imitates evidence far better
than it follows adjectives.

Contract for both files:

- **Loaded whole**, never partially. They are small and they are read together.
- **Never merged with facts.** Voice is not evidence and evidence is not voice.
  The overlay never gets cited in a Sources block, and facts never get lifted out
  of an exemplar — if a claim inside a quote matters, it belongs on a wiki page
  with its own provenance.
- Not linked from `index.md`. The router loads the overlay; the index maps the
  wiki.

## Anti-caricature — mandatory

Every persona brain carries an anti-caricature section, and it is a
**hallucination brake before it is a style note**. Left out, the model reaches
for the loudest three traits and then invents statistics to fill the shape it has
made. Written down, it demonstrably kills invented figures before they reach a
page.

Write it into `persona/voice.md` as its own section, in their specifics rather
than in general advice:

- The **catchphrases and tics that get overused** the moment the voice is
  imitated, and the instruction to use them at the rate the corpus actually uses
  them, which is far lower than an impression of them.
- **What they do not do.** The claims they would not make, the register they
  never use, the topics they decline.
- **Numbers are never improvised.** In their voice, a figure that is not on a
  wiki page does not get said — no rounding to something that sounds right, no
  benchmark recalled from general knowledge and put in their mouth. This is the
  line that does the real work: a confident voice attached to an invented number
  is worse than no brain at all.
- **Confidence is not certainty.** Where the corpus is thin, they say so in their
  own register instead of performing the position they would probably hold.

## index.md

As the subject blueprint describes: one-liners carrying the page's actual
numbers, and a required `## Known gaps`.

`## Known gaps` matters more here, because a persona brain is asked questions
outside its corpus constantly. The gaps register is what lets the brain say, in
their voice, that this is not something they have covered — instead of
generating a plausible position and attributing it to them.

## Calibration

Ask the brain **one question whose answer you already know from the corpus** the
moment it is built — a figure, a stance, a distinction they draw. **Write the
question and the answer it should give into `log.md`**, so the check is a fixed
one that can be re-run after a write-back rather than whatever comes to mind on
the day. Two things get checked at once and both matter:

- **The fact lands.** The number is theirs and it is right.
- **The voice lands.** It sounds like them at the length they would answer at,
  without tipping into impression.

Then ask the member's own intake question. A miss on facts is a Known gap or a
thin page; a miss on voice is usually too few exemplars, or exemplars with no
range — the fix is more of the corpus, not more adjectives in `voice.md`.

## Voice without a corpus

A voice-only brain — the overlay with no wiki behind it — is a **custom shape**,
not this blueprint. It is honoured if a member explicitly asks for it, after one
warning, once: it has **no corpus of its own; it will lean on Claude's own
knowledge and live research**, which is exactly the failure mode the head-to-head
test caught — fluent, confident, and wrong about the person's own numbers.

Never advertise it. It is not offered as an option, not listed as a lighter
alternative, and not suggested when a corpus looks like hard work to assemble.
