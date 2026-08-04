# Demo — Marketing (subject brain, mixed sources)

A **subject** brain built from four arms at once: podcasts, YouTube, web
articles and your own files. This is the prompt that shows the pipeline doing
what it was built for — one manifest shape, four source families, one wiki.

It is also the demo you are meant to edit. The default sources below make it
runnable as written; swapping in your own is the point.

## The prompt

Paste everything in the block. The one line to change is the local folder.

```
Build me a subject brain on modern B2B marketing.

What it's about: how demand actually gets created and converted — positioning
and messaging, channel choice, content, lead generation, funnel and conversion
mechanics, and how to tell which lever is the one that's broken. Advisor stance.
I want to hand it a marketing problem and get a diagnosis, not a checklist.

What it's built from: a mix on purpose — podcast episodes, YouTube, written
posts, and my own notes and reports. I want it to have both the practitioner
talk and the numbers.

Where the sources are:
- Podcasts: "Marketing Against the Grain" and "Everyone Hates Marketers" —
  most recent 25 episodes each. Prefer published transcripts; if an episode has
  none, tell me the transcription cost before you spend anything.
- YouTube: search "b2b demand generation strategy" and "positioning and
  messaging for b2b", 15 videos each, captions only.
- Web: pick a marketing publication you rate, enumerate its post URLs from the
  archive yourself, and take the 30 most substantial. Skip anything paywalled
  rather than working around it.
- My own files: ~/Documents/marketing/ — notes, campaign reports, a few PDFs.
  Read whatever's in there.

What I want to ask it:
- "My demo requests are up but pipeline is flat. What's the actual constraint?"
- "How should I think about positioning for a product in a category that 
  already has a leader?"
- "What's a realistic CAC payback period for B2B SaaS, and what changes it?"
- "Rewrite this landing page headline and tell me why yours is better."

If a source can't be read, name it and move on — don't quietly drop it.
```

## What to expect

- **Four arms means four dependency surfaces.** The podcast and local arms are
  stdlib. YouTube needs `yt-dlp`, web needs `trafilatura`, and any PDF in your
  folder needs `pymupdf4llm`. A missing one fails those sources by name with the
  install line attached; the other three arms still run and the brain still
  builds.
- **Podcasts are where money can appear.** The arm prefers the publisher's own
  `<podcast:transcript>` and only falls back to paid transcription where there
  is none. That is the figure Gate 2 quotes, and it is a bill rather than a
  ceiling because a feed states which episodes ship transcripts.
- **Corpus dedup earns its keep here.** Marketing content restates itself
  across formats constantly — the same argument in a podcast, a video and a
  post. `dedup_corpus.py` flags the pairs so the taxonomy pass distils the claim
  once and cites the original, instead of writing four pages that agree.
- **A mixed corpus contradicts itself**, and that is a feature to watch for.
  Different practitioners give different benchmarks. The wiki should carry the
  spread with its context rather than averaging it into a single fake number.

## Fail questions

Three, one per failure type. Ask each twice: once with the brain attached, once
in a clean session.

> **Every expected answer below is `unverified-until-rebuild`.** They are
> authored against the default source list in the prompt above, and no brain has
> been built from it. If you swap the sources, re-author these after Gate 1 —
> a fail question only works against the corpus it was written for. On rebuild,
> confirm each against the built pages or rewrite it.

---

### 1. Number — the benchmark with no denominator

> **"What's a good CAC payback period for B2B SaaS?"**

**A brain-less agent fails confidently.** It answers "12 months", occasionally
"12–18 months", as a flat industry standard with no conditions attached. It is a
real number from somewhere, delivered as though it applied everywhere.

**Expected from the corpus** — `unverified-until-rebuild`: a spread rather than
a number, with the conditions that move it — contract length and billing terms,
ACV band, whether the motion is sales-led or self-serve, gross margin, and
growth stage — and an explicit note that a payback figure quoted without its
denominator and its segment is not usable. The tell that the brain is working
is that it refuses to give you the single number and says why.

Verify on rebuild: which sources state figures, what the actual spread is, and
that the page carries each figure's scale and date.

---

### 2. Framework — the named structure the corpus actually uses

> **"What framework should I use to work out whether my positioning is the
> problem, or my channel is?"**

**A brain-less agent fails confidently.** It produces a generic marketing
framework — a funnel, a 4P, an AARRR, a "diagnose the leaky bucket" — assembled
from general knowledge and presented as the standard approach. Plausible,
coherent, and not from anyone in particular.

**Expected from the corpus** — `unverified-until-rebuild`: the specific
diagnostic sequence the practitioners in *this* corpus actually run, in their
terms and their order, cited to the pages it came from. What that sequence is
cannot be stated before the brain exists — which is exactly why this question
discriminates. A brain answers with a named framework and a source; a control
answers with a composite of everything it has ever read.

Verify on rebuild: name the framework the wiki settled on, name the page, and
rewrite this section to state it.

---

### 3. Voice — the register that flatters instead of diagnosing

> **"Our content is getting good engagement but no pipeline. What should we
> do?"**

**A brain-less agent fails confidently**, and fails as a register: it validates
the engagement, offers a tidy list of five or six tactics — gated assets, lead
scoring, retargeting, a nurture sequence — and asks nothing. Fluent, helpful,
generic, and it has not diagnosed anything.

**Expected from the corpus** — `unverified-until-rebuild`: an advisor register
that treats "engagement but no pipeline" as a symptom with a small number of
candidate causes, names which one it thinks is most likely and why, and states
what it would need to know to be sure. It leads with a position rather than a
list. Where the corpus does not cover the case, it says so plainly instead of
reaching for tactics.

Verify on rebuild: that the answer names a cause rather than listing fixes, and
that its Sources block points at pages that genuinely bear on the diagnosis.

---

## Rebuild status

**Not built.** The prompt is executable as written; the brain has not been
built, so all three expected answers above are unverified — and the framework
question deliberately cannot be answered until it is. Rebuilding needs network,
`yt-dlp` + `trafilatura` (+ `pymupdf4llm` if your folder has PDFs), and possibly
transcription budget for podcast episodes that ship no transcript. See
[`README.md`](README.md) for the acceptance conditions.
