# Demos

Three worked build prompts. Each one is a **complete paste-in invocation** of
the `brain-builder` skill: it covers everything the intake needs to understand,
so the builder asks nothing and goes straight to the source list.

| Prompt | Kind | Corpus | What it demonstrates |
|---|---|---|---|
| [`ai-expert-karpathy.md`](ai-expert-karpathy.md) | subject | one person's YouTube + blog | two arms, one voice, a technical corpus |
| [`marketing.md`](marketing.md) | subject | YouTube + podcasts + articles + your own files | every arm in one build |
| [`hormozi.md`](hormozi.md) | persona | 30 named YouTube videos | the persona overlay, and the kit's acceptance test |

Paste one in and edit it by talking — the source list is a gate, not a
commitment. The Hormozi prompt is the acceptance test: it is the corpus the
prototype was built from, so it is the one build whose output we know the shape
of in advance.

## Built brains are never distributed

No brain is committed to this repo and none ever will be. The kit ships the
*prompt* that builds a brain, never the brain — that is the rights stance
([`docs/rights.md`](../docs/rights.md)) and it is not negotiable. You rebuild
from the prompt, on your machine, from sources you have lawful access to.

Which is also why the demos below are prompts rather than downloads, and why
these files carry fail questions rather than sample answers.

## Fail questions

A fail question is how you tell a brain apart from a well-briefed agent without
one. Each demo file carries three — the acceptance-test prompt carries four —
and every one meets the same three criteria:

1. **The corpus answers it verifiably.** The answer traces to a page, and the
   page traces to a source. If you cannot point at where the answer lives, it is
   not a fail question.
2. **A brain-less agent fails it *confidently*.** Not "I don't know" — a fluent,
   plausible, wrong answer delivered with no hedging. A question a control
   politely declines proves nothing; a question it gets wrong while sounding
   right proves everything.
3. **Coverage across three failure types.** *Number* — a benchmark or figure the
   control invents or mis-scales. *Framework* — a named structure the control
   reconstructs from the name. *Voice* — a register the control caricatures.

Run each question twice: once in a session with the brain attached, once in a
clean session without it. Both answers side by side is the demo.

## Drop-week acceptance test

**This is the acceptance test for the kit, and it has not been run.** The three
prompts are authored and executable; the three brains are not built.

Running it needs a machine this session did not have:

- **Network**, for every arm.
- **Browser cookies for YouTube** — the ingestion arm reads them from Chrome by
  default (`YT_COOKIES_FROM_BROWSER`, set it to `none` to disable). A datacentre
  IP is the block-prone environment; a member's home machine is the good one.
- **Hours of wall clock.** The prototype's 30-video corpus took ~30 minutes of
  ingest and distillation with 8 parallel agents, on captions that already
  existed.
- **Possibly money.** Any source without a published transcript falls back to
  paid transcription. The plan gate prices it before anything is spent.

The pass condition, per brain:

1. The prompt builds without stopping — failures land in `log.md` by name,
   nothing is silently skipped.
2. `lint.py` exits 0 and `verify_numbers.py` exits 0.
3. Every fail question below is answered correctly by the attached brain, and
   incorrectly by a clean session — and each expected answer marked
   `unverified-until-rebuild` is either confirmed against the built corpus or
   rewritten to what the corpus actually says.

That last clause is the honest part. The Hormozi literals were sourced from the
prototype build and are marked with the page and video they came from. The
Karpathy and Marketing literals are authored to the criteria but their corpus
answers cannot be confirmed until the corpus exists, and they say so inline
rather than implying a certainty nobody has yet.
