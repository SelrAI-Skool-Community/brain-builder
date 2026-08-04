# Demo — AI expert, from Karpathy's YouTube and blog (subject brain)

A **subject** brain: a wiki organised by concept, answering as an advisor who
holds the material. One person's published thinking, but *about* the subject
rather than *as* the person — the difference between this and
[`hormozi.md`](hormozi.md) is the blueprint, and it is the clearest illustration
of what "kind" means in this kit.

Two arms in one build: YouTube for the lectures, web for the written posts.

## The prompt

Paste everything in the block.

```
Build me a subject brain on how large language models actually work, from
Andrej Karpathy's published teaching.

What it's about: the mechanics of LLMs and neural networks as he teaches them —
tokenization, training and pretraining, fine-tuning and RLHF, transformer
internals, what these models can and can't do, and how he thinks about building
software with them. A subject brain, advisor stance. I want to ask it questions
and get his substance, not an impression of him.

What it's built from: his YouTube lectures and his blog posts. The lectures are
long and dense — the "Zero to Hero" series, the build-it-from-scratch walkthroughs,
the deep dives and the talks. The posts are shorter and carry the framings.

Where the sources are:
- YouTube: https://www.youtube.com/@AndrejKarpathy — take the channel, cap it at
  30 videos, longest first. Captions where they exist.
- Blog: https://karpathy.bearblog.dev/ and https://karpathy.github.io/ —
  enumerate the post URLs from each archive page yourself, then ingest the posts
  individually. Don't ingest the archive index pages as content.

What I want to ask it:
- "Explain what a tokenizer actually does and why it causes so many weird 
  model failures."
- "What's the difference between pretraining, fine-tuning and RLHF, in his terms?"
- "How does he think about how much to trust an LLM's output when coding?"
- "What does he say is actually missing before agents work properly?"

Where the corpus is thin, say so rather than filling it in from general
knowledge — the whole point is that I can tell the difference.
```

## What to expect

- **The web arm takes article URLs, not a site.** It has no crawler, which is
  why the prompt asks the builder to enumerate the post URLs first. That
  enumeration is research, and research is the builder's job — it should not
  come back and ask you for a list.
- **`pip install trafilatura` and `pip install yt-dlp`** are both needed here,
  one per arm. If either is missing, that arm's sources fail by name with the
  install line on the record, and the other arm still runs.
- **Long lectures, so caption dedup carries the weight.** Several of these
  videos are multi-hour. Expect the ingest summary to report far fewer words
  than raw caption size suggests; that is dedup working.
- **A technical corpus makes number verification earn its keep.** Parameter
  counts, context lengths, vocabulary sizes and learning rates are exactly the
  figures ASR mangles. `verify_numbers.py` closes the build for a reason.

## Fail questions

Three, one per failure type. Ask each twice: once with the brain attached, once
in a clean session.

> **Every expected answer below is `unverified-until-rebuild`.** The questions
> are authored to the criteria and targeted at what this corpus should contain,
> but no brain has been built from it yet, so no answer here has been traced to
> a page. On rebuild, confirm each one against the built corpus or rewrite it to
> what the corpus actually says. Do not treat these as facts in the meantime.

---

### 1. Number — the horizon everyone rounds down

> **"How long until AI agents actually work well enough to replace a junior
> engineer? Give me a timeframe and your reasoning."**

**A brain-less agent fails confidently.** It reproduces the industry line — that
this is the year of agents, that it is twelve to eighteen months out — in a
fluent, hedge-free paragraph. The failure is that it is repeating consensus
marketing back at you, and sounding measured while doing it.

**Expected from the corpus** — `unverified-until-rebuild`: he pushes back
explicitly on the one-year framing and argues for a horizon roughly an order of
magnitude longer, with the reasoning being an enumerated list of missing
capabilities rather than a vibe. Verify on rebuild: the exact horizon he states,
the exact list of deficits he names, and which video or post they come from.

---

### 2. Framework — the named distinction

> **"What does Karpathy mean when he says LLMs are not animals? Walk me through
> the distinction he draws."**

**A brain-less agent fails confidently.** It has the shape of the argument in
its general knowledge but not the specifics, so it produces a plausible
reconstruction — something about embodiment, or evolution, or grounding —
delivered as though quoting him. It will not flag that it is reconstructing.

**Expected from the corpus** — `unverified-until-rebuild`: a specific pairing in
which LLMs are not the product of an evolutionary process but an imitation
learned from human output, with a named counterpart term he uses for what they
are instead, and a conclusion about what that implies for how AI research should
proceed. Verify on rebuild: his actual terms, his actual conclusion, and whether
this is in the corpus at all — if it is not, this question moves to Known gaps
and gets replaced.

---

### 3. Voice — the register that gets flattened

> **"Should I be reviewing the code an LLM writes for me, or is that going
> away?"**

**A brain-less agent fails confidently in one of two directions**, both generic:
the hype answer (review is a transitional cost, autonomy is coming) or the
caution answer (always review everything, AI is unreliable). Both are positions
about AI in general, delivered with no mechanism attached.

**Expected from the corpus** — `unverified-until-rebuild`: a calibrated middle
that is neither, expressed as a control you turn rather than a yes/no — how much
autonomy to hand over depends on how verifiable the output is and how large the
change is, with a stated preference for small reviewable increments and a
specific position on why the last stretch of reliability is the expensive one.
Verify on rebuild: the actual framing, the actual heuristics, and the pages they
land on.

---

## Rebuild status

**Not built.** The prompt is executable as written; the brain has not been
built, so all three expected answers above are unverified. Rebuilding needs
network and `yt-dlp` + `trafilatura`. See [`README.md`](README.md) for the
acceptance conditions.
