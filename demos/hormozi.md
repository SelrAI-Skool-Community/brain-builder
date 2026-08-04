# Demo — Alex Hormozi (persona brain)

A **persona** brain: subject core plus a voice overlay, answering *as* the
person rather than about him. This is the kit's acceptance test — the same
30-video corpus the prototype was built from, so it is the one build whose shape
is known in advance.

Expect roughly 220,000 words of transcript in, a wiki in the region of 50 pages
out, and a `persona/` overlay of `voice.md` plus 20–30 verbatim exemplars.

## The prompt

Paste everything in the block.

```
Build me a persona brain on Alex Hormozi.

What it's about: his business teaching — offers and money models, lead
generation, scaling and operations, business diagnosis, content and audience,
mindset, and AI in business. I want it to answer as him, in his voice, not
about him at arm's length.

What it's built from: 30 videos from his YouTube channel, listed below. They
were hand-picked from the channel for business substance rather than reach —
the long teardowns and the mechanism-heavy explainers, not the clip-farm shorts.
Captions only; don't pay to transcribe anything unless a video has none and
you tell me the cost first.

Where the sources are:

  https://www.youtube.com/watch?v=Jmkq5RLjm0U  # If I Wanted To Grow An Audience In 2026, I'd Do This
  https://www.youtube.com/watch?v=qsXxckCbci0  # How To Grow ANY Business FASTER (Masterclass)
  https://www.youtube.com/watch?v=N5MExtki_VI  # If I Wanted To Scale A Service Business In 2026, Here's What I'd Do
  https://www.youtube.com/watch?v=A_tx40lNpf8  # The Mathematics of Business, Explained
  https://www.youtube.com/watch?v=zzleYxkf39k  # Building a $1,000,000 Business for a Stranger in 42 Minutes
  https://www.youtube.com/watch?v=jqo0lVveh98  # Watch This If You Have a Service Business
  https://www.youtube.com/watch?v=8C_6qojTA78  # Helping E-Commerce Business Owners Scale
  https://www.youtube.com/watch?v=ZuJryiwxjDw  # Why you aren't making as much money as you want
  https://www.youtube.com/watch?v=Mst4hreQYl0  # Watch This To Generate 1000s of Leads (In Any Niche)
  https://www.youtube.com/watch?v=nSQdjim8CsE  # Making Money is a Game (Here's the Cheat Code)
  https://www.youtube.com/watch?v=6BQ3whjWG3M  # How the Top 1% Actually Think About Money
  https://www.youtube.com/watch?v=j2TZMFkj71Q  # Building a $3,000,000 Business for a Stranger in 31 Minutes
  https://www.youtube.com/watch?v=mr4Pw66_490  # If I Wanted to Create a Business That Runs Itself, Here's What I'd Do
  https://www.youtube.com/watch?v=sL16tsGafcQ  # If You Want To Create Wealth In 2026, Watch This (4 Paths)
  https://www.youtube.com/watch?v=dMZ-n2KSlxE  # My Actual Social Media Strategy For 2026
  https://www.youtube.com/watch?v=XGm2ERU9qtA  # 15 Brutal Truths I Know at 36 That I Wish I Knew at 20
  https://www.youtube.com/watch?v=hnmBXTyMFKI  # You can make way more money than you think
  https://www.youtube.com/watch?v=9q5ojtkqsBs  # How to Win With AI in 2026
  https://www.youtube.com/watch?v=3fsJFUvA6Ts  # What Makes The Perfect Business (5 Things)
  https://www.youtube.com/watch?v=sGakuNs9mT4  # How to Speak So Well People Give You Money
  https://www.youtube.com/watch?v=3yAiVjcImQ4  # I Blew Up a Business Through 3 Small Changes (Just Copy Me)
  https://www.youtube.com/watch?v=XwzU4RikbGs  # You're Setting Goals Wrong
  https://www.youtube.com/watch?v=-j8_YCWZ05Q  # How to Get Your Customers to Stay FOREVER
  https://www.youtube.com/watch?v=uWdIgftpvBI  # If I Started A Business in 2026, I'd Do This
  https://www.youtube.com/watch?v=jfW6gL6hKhk  # If I Wanted to Make My First $100K in 2026, I'd Do This
  https://www.youtube.com/watch?v=rMJIOK_FgJk  # The 6 Levels of Making Money
  https://www.youtube.com/watch?v=hHkdbr6_JJs  # How Acquisition.com Makes Money
  https://www.youtube.com/watch?v=fr78adfAnuA  # How to Use AI in Your Business in 2026
  https://www.youtube.com/watch?v=XsWSvz-aewA  # The New Way of Making Content In The Age of AI
  https://www.youtube.com/watch?v=k5-57282taI  # How The Top 1% Actually Think About Trust

What I want to ask it:
- "My close rate is 80% — what does that tell you about my pricing?"
- "Diagnose this business: $40k/month, service, one founder selling, 
  three-month average retention. What's the constraint?"
- "What LTV:CAC should I be running for a service business with a sales team?"
- "Write me a 200-word post about pricing, in your voice."

Be honest about what the corpus doesn't cover — his books aren't in it and I
don't want it pretending otherwise.
```

## What to expect

- **Gate 1** redraws this list as one YouTube group of 30 with a one-line
  reason. Edit it by talking if you want a different cut.
- **Gate 2** states the shape (persona), the destination (`~/brains/hormozi/`),
  the count, and the transcription figure. For a captioned corpus that figure
  should be a ceiling, not a bill — auto-captions exist for all 30, so nothing
  should need paying for.
- **Caption dedup matters here.** YouTube auto-captions roll, repeating each
  line with a word or two appended; naive stripping inflates the word count
  3–4×. If your build reports 700k+ words, dedup did not run.
- **The anti-caricature section in `persona/voice.md` is mandatory**, not a
  style note. In the prototype it demonstrably killed two invented statistics
  before they reached a page.
- **Known gaps should name the books.** The corpus is 30 videos; *$100M Offers*
  and *$100M Leads* are not in it, and neither are cold email, cold call or paid
  ad mechanics.

## Fail questions

Four, because this is the acceptance test. Ask each one twice: once with
`hormozi` attached, once in a clean session with no brain.

---

### 1. Number — the benchmark that inverts

> **"Our community is running about 6% monthly churn. Is that good or bad, and
> what should I do about it?"**

**A brain-less agent fails confidently.** This is the documented head-to-head
failure from the prototype: a deliberately strong control, told to act as an
expert on him, called 6% monthly churn *middling* and recommended fixing it. It
did not hedge.

**The corpus says the opposite.** Platform average is 20% monthly churn (80%
retention); best groups are under 10%; bad groups are over 30%. 6% is top-tier —
the answer is that retention is not this business's constraint and the effort
belongs elsewhere. A correct answer also carries the caveat the index page
attaches: the benchmark is consumer/online-services data, not home services or
insurance, and should not be generalised.

*Corpus answer verified* — `wiki/scaling-and-operations/churn-and-retention-mechanics.md`,
from *How to Get Your Customers to Stay FOREVER* (`-j8_YCWZ05Q`). Cross-recorded
in [`docs/research/prototype-findings.md`](../docs/research/prototype-findings.md).

---

### 2. Number — the benchmark everybody misquotes

> **"What LTV:CAC ratio should I be targeting? I run a service business with a
> phone sales team."**

**A brain-less agent fails confidently.** It answers "3:1", the benchmark
everyone knows, usually with a line about 1:1 being unsustainable. Delivered
flatly, as settled fact.

**The corpus says 9:1**, and gives the mechanism rather than the number: score
three stages 0 or 1 by whether a human sits in them — attraction, conversion,
delivery. Ads to a checkout for software is 0 humans and 3:1. Ads to a phone
sales team delivering a service is 2 humans, which is 9:1. Three humans is 12:1.
The reason is lumpiness: at 3:1 with one rep, hiring a second rep — who will be
worse, at least at first — drops you under the ratio immediately. The 3:1
benchmark is real but applies to roughly 5% of businesses.

*Corpus answer verified* — `wiki/offers-and-money-models/ltv-to-cac-ratios.md`,
from *The Mathematics of Business, Explained* (`A_tx40lNpf8`).

---

### 3. Framework — the named structure

> **"Walk me through SPCL. Which of the four matters most, and why?"**

**A brain-less agent fails confidently.** SPCL is not a widely indexed acronym,
so a control reconstructs it from the letters — "Situation, Problem,
Complication, Learning" or similar — and delivers a coherent, entirely invented
framework. This is the cleanest confident failure in the set, because the
control has no idea it is guessing.

**The corpus says Status, Power, Credibility, Likeness** — four stackable
influence stats, where influence is defined operationally as likelihood of
compliance with a request. Status is controlling reinforcers in an environment.
Power is say–do correspondence: you give a direction, it works, the next request
lands easier. Credibility is third-party observable proof. Likeness is
relatability. **If forced to pick one, pick power.** None are binaries; they
stack, and their worked maximum is your parents.

*Corpus answer verified* — `wiki/content-and-audience/spcl-influence-framework.md`,
from *My Actual Social Media Strategy For 2026* (`dMZ-n2KSlxE`) and
*If I Wanted To Grow An Audience In 2026* (`Jmkq5RLjm0U`).

---

### 4. Voice — the register a mimic gets wrong

> **"Write me a 150-word pep talk, as Alex Hormozi, for a founder whose sales
> have been down three months running."**

**A brain-less agent fails confidently**, and fails in a specific, gradeable
way: it produces the gym-bro hype voice. Shouting, "LET'S GO", profanity as
background texture, an epigram every sentence, invented precise statistics to
sound authoritative, and mindset with no mechanism under it. It reads like a
LinkedIn post about him.

**The corpus says he is not a hype man.** The overlay's anti-caricature section
names each of these as the mimic's tell. What he actually does: converts the
feeling into arithmetic — the single most characteristic move in his register —
gives the mechanism before the aphorism, swears once at most and only at the
emotional peak, uses numbers he *has* rather than numbers he invents (he is far
likelier to say "call it 60 to 70%" than to fabricate a decimal), implicates
himself in the failure rather than talking down, and offers the listener an exit
from his own advice. Second person throughout, no closing question.

Grade it against `persona/voice.md`'s anti-caricature list rather than by feel —
that is what the section is for.

*Corpus answer verified* — `persona/voice.md`, distilled wide-and-shallow across
all 30 videos.

---

## Rebuild status

**Not rebuilt through the kit yet.** The four expected answers above come from
the prototype build of this same corpus (planning ticket CORE-128, recorded in
[`docs/research/prototype-findings.md`](../docs/research/prototype-findings.md)),
which is why they are marked verified rather than `unverified-until-rebuild`.

What the rebuild has to confirm is that the *kit* reproduces them: same corpus,
same figures, arrived at through the shipped arms, the shared taxonomy pass, the
number-verification pass and lint — none of which the prototype had. See
[`README.md`](README.md) for the full acceptance conditions.
