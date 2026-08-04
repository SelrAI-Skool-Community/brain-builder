---
name: brain-builder
description: >
  Build a portable knowledge brain — a standalone folder of markdown that an
  agent navigates like a wiki, answers from as a subject-matter expert, cites,
  and admits the limits of. Use this whenever someone wants to build a brain,
  turn a folder of notes, docs, transcripts or exports into something Claude can
  answer from, or make an expert on a topic: "build me a brain about X", "turn
  these files into a brain", "I want Claude to know everything in this folder",
  "make an expert on Y I can ask questions". Use it too when someone has a pile
  of material and wants it made genuinely useful rather than summarised once —
  that is a brain, even when they never use the word. Runs the whole build:
  intake, source list, plan gate, ingest, wiki, router, attach, demo.
---

# Brain Builder

Turn a body of source material into a **brain**: a standalone folder of markdown
at `~/brains/<slug>/` that can be switched on for any AI tool on the machine,
that answers as an expert who holds the material, cites the page you would edit
to fix an error, and says so plainly when a question lands inside its subject but
outside the material it was built from.

Invoke by name (`/brain-builder`) or by saying any of it in your own words. One
paste-in prompt is a complete invocation — if the opening message already tells
you what the brain is about, what it is built from, where the material lives and
what the member wants to ask it, **ask nothing** and go straight to Gate 1.

**One arm per source family**, and every one of them returns the same manifest:
local files, PDFs and EPUBs, YouTube, web articles, and podcasts (Apple
Podcasts or any RSS feed). Instagram, TikTok, X, LinkedIn and Spotify's own
player are out of v1 — when a member names one, say so in a line and offer what
does work: an export, a download, or the show's RSS feed.

## What you are building

```
~/brains/<slug>/
  SKILL.md    the generated router — the brain's entire interface
  index.md    the map: one-liners carrying real numbers, + ## Known gaps
  wiki/       the synthesized knowledge; interior taxonomy free per brain
  raw/        immutable ingested source material, fenced, kept in-tree
  log.md      build + write-back timeline
  CHANGELOG.md
  persona/    overlay, when the blueprint declares one: voice.md + exemplars.md
  standing/   overlay, when the blueprint declares one: standing facts and policies
```

Zero infrastructure: no RAG, no embeddings, no database, no server. Files only.
Retrieval is an agent starting at `index.md` and following links.

The scripts sit next to this file, and `scripts/…` below means **this skill
directory** — not the member's working directory, which is where you are
actually running. Resolve it once at the start of a build and use the absolute
path from then on:

```bash
KIT=~/.claude/skills/brain-builder/scripts   # or wherever this skill was installed
python3 "$KIT/scaffold.py" --list-blueprints
```

Stdlib-only Python 3 except the ingestion readers, which each import their own
library and name the `pip install` line if it is missing:

| Step | Call |
|---|---|
| List the kinds on offer | `python3 "$KIT/scaffold.py" --list-blueprints` |
| Stand the brain up | `python3 "$KIT/scaffold.py" --title "…" --domain "…" --kind subject [--slug …] [--at ~/brains]` |
| Ingest local files | `python3 "$KIT/ingest_local.py" <paths…> --into <brain> --json` |
| Ingest PDFs / EPUBs | `python3 "$KIT/ingest_docs.py" <paths…> --into <brain> --json` |
| Ingest YouTube | `python3 "$KIT/ingest_youtube.py" <url-or-search…> --into <brain> [--limit N] [--transcribe] --json` |
| Ingest web articles | `python3 "$KIT/ingest_web.py" <urls…> --into <brain> --json` |
| Ingest podcasts | `python3 "$KIT/ingest_podcast.py" <apple-url\|rss-url\|"show name"…> --into <brain> [--limit N] [--transcribe] --json` |
| Price transcription (Gate 2) | `python3 "$KIT/ingest_podcast.py" --estimate <show…>` · `python3 "$KIT/ingest_youtube.py" --estimate <url…>` · `python3 "$KIT/transcribe.py" --estimate <seconds…>` |
| Find sources that repeat each other | `python3 "$KIT/dedup_corpus.py" <brain> --json` |
| Check the figures | `python3 "$KIT/verify_numbers.py" <brain>` |
| Generate the router | `python3 "$KIT/gen_router.py" <brain>` |
| Lint (last — it checks the router too) | `python3 "$KIT/lint.py" <brain>` |
| Show the finished brain as a picture | `python3 "$KIT/open_in_obsidian.py" <brain> [--check]` |

## How to say it

The member brings three things: what they want out of the brain, where the
material comes from, and how it should behave. **How it gets built is this kit's
job, and the kit's vocabulary is not theirs.** Wiki, taxonomy, cluster,
frontmatter, router, lint, slug, symlink — those are how you think, not how you
narrate.

That is not permission to hide anything. **Never abstract the machine away —
explain it.** Where a technical word genuinely earns its place, use it *and*
define it in the same breath, once, at first use:

> "I'll write it up as a wiki — a folder of small linked pages, one idea per page
> — so answers can point at the exact page they came from."

Source talk is safe and stays: members know what their own files, videos and
podcasts are, and counts of them mean something. It is the machinery that needs
translating.

The right-hand column below is **register, not a script**: match its plainness
and its level of explanation, then use the real numbers, paths and field names
from the build in front of you. Never emit these lines verbatim.

| Not this | This |
|---|---|
| "deciding the taxonomy" | "working out the map — which topics there are, and what belongs on each page" |
| "one writer per cluster, in parallel" | "writing the sections at the same time, one per group of topics" |
| "generating the router" | "writing its front page — the summary Claude reads to know when to open the brain and which page to go to" |
| "running lint" / "lint clean" | "checking it holds together — every page carrying the details it needs, every link going somewhere real. All clean." |
| "the frontmatter is invalid" | "one page had `volatility: drifting` at the top, and that setting only takes `fast`, `slow` or `stable` — set it to `fast`" |
| "the corpus" | "your material" / "the 86 sources" |
| "OKF frontmatter with a `type`" | *nothing — this one is yours alone* |

Note the frontmatter row: the fix is to **name the field, the bad value and the
allowed ones** in words the member can follow — not to shrink it to "a setting
was wrong". Explaining beats summarising every time.

**Do not name other AI tools unless it is actually the member's situation.**
Claude Code is the tool in front of them, and **"harness" is never a word to use
with a member** — say "the tool you're using", and name it. Codex, Gemini and the
rest come up only in the three cases the `brain-toggle` skill lists: they raise
one by name; the brain genuinely is on in more than one and the answer would be
wrong without saying so; or they asked for an unusual install. So
*"switched on for Claude Code — the tool you're using right now"* when it went to
one, and *"switched on for Claude Code and for Codex — two separate tools on this
machine, each with its own switch"* when it really did go to both. **Never report
two as one**; under-reporting where a brain landed is a lie, not brevity.

## Phase 1 — Intake

Interview to **shared understanding, not question coverage**. Four things have
to be understood before you can propose anything. They can come from the member,
from the material, or from your own research — the source does not matter, only
that you actually understand them:

1. **What the brain is about.** This selects the blueprint.
2. **What it is built from.** The kind of material, and roughly how much.
3. **Where the sources are.** A folder path, a channel, a feed, a reading list —
   whatever the arms get pointed at, per source family.
4. **What the member wants to ask it.** Keep these questions verbatim — they
   are the calibration at the end, and the seed of `## Known gaps`.

How to run it:

- **A full mind-dump earns zero questions.** If the opening message covers all
  four, acknowledge in a line and move to Gate 1. Asking anyway is the most
  common way this skill annoys people.
- **Research instead of asking anything look-up-able.** If a folder is named,
  look in it — count the files, read a few, see what the material actually is.
  Never ask "what format are your files in?" when you can list the directory.
- **Ask about intent, never architecture.** The member is never asked how to
  organise the wiki, how many pages there should be, what the taxonomy is, or
  which files should become which page. Those are your job. Questions worth
  asking are about *purpose* — what they'll ask it, what it must not get wrong.
- **Batch what is left into one message**, two or three questions at most, in
  plain language. This is a conversation, not a form.

## Phase 2 — Shape

Kinds are **blueprints, not types**, and they live as files:

```bash
python3 "$KIT/scaffold.py" --list-blueprints
```

Read that list at runtime rather than assuming which kinds exist — adding a kind
is adding a file, and this skill is not edited when one lands. Read the chosen
blueprint's own file before building; it describes the shape you are aiming at.

**Suggest, explain, confirm in a line.** "This is a subject brain — a wiki, which
is a set of small linked pages with one idea on each, organised by topic and
answering you like an advisor. Sound right?" Then move on. Do not
present a menu of kinds and ask the member to choose: they told you what they
want in Phase 1, and picking the shape is your job.

**One blueprint per brain.** Nothing merges at build time — a member who wants
two shapes gets two brains, stacked at attach time.

**Custom shapes are honoured, never advertised.** If a member explicitly asks for
a shape no blueprint covers, build it — after one warning, once, then drop it.
For a brain with no corpus of its own (a voice-only brain, say), the warning is
that it has **no corpus of its own; it will lean on Claude's own knowledge and
live research**. Never lint-enforce a custom shape, and never bring the option up
unprompted.

## Gate 1 — the source list

Propose the sources, **grouped by platform, with counts and a one-line reason
each**:

```
Local files — 34
  ~/Documents/baking/notes/     18 md   your own bench notes, the numbers live here
  ~/Documents/baking/refs/      12 pdf  the reference books, read by the docs arm
  ~/Downloads/starter-log.csv    1 csv  the feeding log, 14 months of timings

YouTube — 30
  @thebreadchannel               24     the technique series, where the timings are
  the six "starter troubleshooting" videos  6  the questions you said you ask most

Podcasts — 12
  Proof (Apple Podcasts)         12     the miller interviews, for the flour numbers
```

One group per platform, because that is how the member edits it — "drop the
PDFs" and "cut the podcast to six" are the two things they say.

Then: *"Anything to add or drop?"* This gate is **edited by talking** — the
member says "drop the PDFs, add my Obsidian vault" and you redraw the list. Loop
until they approve. Say plainly what no arm can read rather than quietly
dropping it — DRM'd books and Spotify-exclusive shows have no way in, and that
is a line at this gate, not a surprise at the end.

## Gate 2 — the plan gate

One message, four facts, then one approval:

- **Shape** — the blueprint, in a phrase.
- **Where it lands** — stated, never asked: "→ `~/brains/sourdough-baking/`".
  If the member changes it in passing, take the change and carry on.
- **Source count** — what will actually be ingested.
- **Transcription** — hours and cost, from the estimator, **once**. Never quote
  a figure you worked out in your head, and never mention money again after this
  gate:

  ```bash
  python3 "$KIT/ingest_podcast.py" --estimate <show…>   # prices the feed
  python3 "$KIT/ingest_youtube.py" --estimate <url…>    # the ceiling for video
  python3 "$KIT/transcribe.py" --estimate <seconds…>    # prices anything else
  ```

  For local files, documents and web articles this is **none, $0** — say it
  anyway, because it is the line that stops a surprise on the arms that do
  transcribe. A feed says which episodes ship transcripts, so its figure is the
  bill; YouTube does not, so its figure is a ceiling and is quoted as one.
  A cheaper engine exists (`--engine groq`) at roughly a fifth the price, for
  **rough indexing only** — its pages are marked never-quote. Do not offer it
  unless the member raises cost; never make it the default.

Get **one** approval and then build. No further questions during the build: if
something needs a decision mid-build, make it and note it in the report. The
approval at this gate is what authorises `--transcribe` on the arms that take
it; without it they record a caption-less source rather than spending money.

## Phase 3 — Build

Narrate at **phase level with counts** — one line per phase, never file by file,
never a running commentary. Five phases: ingest → taxonomy → pages → router →
lint. The last two share one line; overlays add a sixth line on the kinds that
have them.

Those five names are yours. The lines the member reads use the wording in *How
to say it* above. **Counts, failures and caveats survive the translation intact**
— it is the vocabulary that changes, never the honesty.

**Ingest — one arm per source family, then one dedup pass.**

```bash
python3 "$KIT/scaffold.py" --title "<title>" --domain "<one line>" --kind <kind>
python3 "$KIT/ingest_local.py" <paths…>   --into <brain> --json   # md/txt/csv/json/docx
python3 "$KIT/ingest_docs.py" <paths…>    --into <brain> --json   # pdf/epub
python3 "$KIT/ingest_youtube.py" <urls…>  --into <brain> --json   # channels, playlists, searches
python3 "$KIT/ingest_web.py" <urls…>      --into <brain> --json   # articles
python3 "$KIT/ingest_podcast.py" <shows…> --into <brain> --json   # Apple Podcasts or any RSS
python3 "$KIT/dedup_corpus.py" <brain> --json                     # after every arm has run
```

`scaffold.py` writes the skeleton and — importantly — the `index.md` frontmatter
the router generator reads, including the stance taken from the blueprint. Route
each group from Gate 1 to its arm and run only the arms that have sources; add
`--transcribe` only where Gate 2 priced it.

Every arm behaves the same way, which is what makes them safe to run in a row:
counts out, never an exception, and dead, empty, duplicate, unreadable and
refused sources recorded in the manifest and appended to `log.md`. Re-running
after a Gate 1 edit adds material rather than overwriting any — `raw/` is
immutable, and YouTube keeps an archive so a re-run does not re-fetch.

**Fail loudly, in this order.** Publisher transcript → transcription fallback →
a named record. A video with poisoned captions, a paywalled article, a
DRM-refused book and a Spotify exclusive all end up in `log.md` by name. None of
them is ever silently skipped, and none of them is worked around.

An arm exits non-zero only when **nothing** came out of what it was given; that
is the single condition that stops a build. Stop, say which arm it needs or what
the corpus was, and talk to the member. Never build an empty brain.

**Close the phase with one line** covering every arm together, and let `log.md`
hold the detail:

> `↳ Read 86 sources (412,900 words) — 3 were empty, 2 were duplicates, 1 was paywalled and is set aside unused. Another 2 are kept, but say the same thing as sources you already have.`

**Taxonomy — one shared pass, before any page is written.** Read across the
whole of `raw/` and decide the concept map for the brain in one pass: the pages,
their names, what belongs on each. This happens **before** any parallel work,
because section agents that each invent their own taxonomy produce a wiki that
overlaps in some places and dangles in others. Fix the map first; then fill it.

> `↳ Mapped the ground: 11 topics, one page each, gathered into 3 areas.`

Use `dedup_corpus.py`'s pairs here: where one source restates another, distil
the claim **once** and cite the original. Four `raw/` pages saying the same
thing is a compilation, not four sources agreeing.

**Pages.** Write `wiki/` from the agreed map — this is where parallel section
agents earn their keep, one agent per cluster, each working to the shared map.
Every page: OKF frontmatter with a `type`, the sources it was distilled from,
the answer first, and **numbers kept exact with their context** — a figure keeps
its unit, its denominator and its date, because a number that lost its scale is
not citable however well it is sourced. Never invent a fact to fill a page; a
thin page is honest, a padded one is not.

> `↳ Wrote 11 pages, with 38 links between them.`

**Overlays — where the blueprint declares one.** A subject brain has none and
this step is skipped. The other two are not optional extras: a persona brain
without its overlay is a subject brain wearing the name of a person.

- **`persona/`** — `voice.md` and `exemplars.md`, **both required**. `voice.md`
  is a thin list of *observable* rules, each one pointable-at in the corpus;
  `exemplars.md` is **10–20 verbatim excerpts chosen for range**, short-form
  register included, because the exemplars do the heavy lifting and a rule that
  cannot be pointed at is a guess. The overlay is loaded whole, never merged
  with facts, and **never cited** — so it is not linked from `index.md`.
- **`standing/`** — standing facts and policies, one page each. It is
  **unfenced**: routed exactly like `wiki/`, so its pages carry OKF frontmatter
  (lint holds them to it) and **are linked from `index.md`** like any other
  routed page.

> `↳ Voice: a short list of rules for how they talk, each one pointing at where it shows in the material, plus 14 word-for-word examples.`

**`index.md` — a first-class step, not a formality.** The one-liners are what
routing runs on, so **each one carries the page's actual numbers**, not a topic
label. "Hydration — 70 % baseline for 12.5 %-protein flour; wholemeal drinks 5–8 %
more" routes; "Hydration — about hydration" does not. Leave the frontmatter
`scaffold.py` wrote intact: `slug`, `title`, `domain`, `kind` and `stance` are
what `gen_router.py` reads, and the router cannot be generated without them.

**Router, then lint** — in that order, and lint closes the build (spec.md §5, as
amended: the router *is* part of the brain, and `lint.py` checks that `SKILL.md`
exists and that its frontmatter can fire, so linting first always fails on the
brain's own front door).

```bash
python3 "$KIT/gen_router.py" <brain>   # reads index.md frontmatter
python3 "$KIT/lint.py" <brain>         # skeleton, frontmatter, links, router
```

Regenerating the router is a no-op diff, so fix anything lint reports and run
both again without thinking about it.

> `↳ Front page written, and the whole thing checks out — every page carrying the details it needs, every link going somewhere real.`

## Phase 4 — Self-check

Two passes close every build:

1. **Lint** — until it exits 0, regenerating the router after any fix. Dangling
   links cluster on exactly the concepts people reach for most, so they matter
   more than they look.
2. **Number verification** — `python3 "$KIT/verify_numbers.py" <brain>`, which
   catches figures their own sentence contradicts, spoken numbers the digits
   disagree with, and figures that lost their unit. Errors exit 1; fix them
   against `raw/` before the brain ships. Then spot-check by hand what a script
   cannot: the figures in `index.md` and the most-cited pages, traced back to
   the source. **A number that cannot be traced back comes out of the brain**;
   it does not get softened into a vague claim.

**Whatever is left over becomes `## Known gaps` in `index.md`, not a build
error.** Thin areas, sources that failed, intake questions the corpus turned out
not to answer — all of it belongs in the register the brain refuses from. A brain
that knows what it does not know is the whole point.

## Phase 5 — Finish by demo

A build is not finished when the files exist. It is finished when the member has
seen it work.

1. **Attach it** with the `brain-toggle` skill — that skill owns the mechanics.
   If it is not installed, the manual stand-in is one symlink:
   `mkdir -p ~/.claude/skills && ln -sfn ~/brains/<slug> ~/.claude/skills/<slug>`
   Say it as *"switched on for Claude Code — new sessions will have it, no
   restart needed"*. Only name a second tool if you actually turned it on there
   too, and then explain the pair once rather than assuming they know.
2. **Demo it** with one of the member's **own** questions from Phase 1 — asked
   verbatim, answered by the brain. Their question, their material, their
   answer, in front of them.
3. **Show it as a picture.** A brain is small pages linked to each other, which
   is exactly what Obsidian draws — so end by opening it there and letting the
   member see their own material as a map of connected dots.

   ```bash
   python3 "$KIT/open_in_obsidian.py" <brain>          # installs if needed, then opens
   python3 "$KIT/open_in_obsidian.py" <brain> --check  # state only, changes nothing
   ```

   It adds the brain folder to Obsidian as a *vault* — Obsidian's word for a
   folder it reads — and opens it. If Obsidian is not on the machine it installs
   it, and **you say that first, in one line, before you run it**: *"Installing
   Obsidian — a free app that shows your brain as a visual map of linked
   pages."* Never install anything silently.

   Opening the vault is all that can be automated. There is no link that goes
   straight to the picture, so **name the one click**: *"press Cmd+G — Ctrl+G on
   Windows and Linux — or the graph icon down the left side, and you'll see
   every page and every link between them."*

   **This cannot fail the build.** When it can't open — no way to install, no
   Obsidian, a launch that didn't take — it exits 1 and prints what to do
   instead: the download link, or which folder to open as a vault. That is one
   calm line to the member and nothing more. The brain is finished either way,
   and this is the one step worth losing.

4. **Report in a few lines**: what was built, how many sources and pages, where
   it lives, the one summary line for anything that failed, and what the Known
   gaps say. Plain words throughout — this is the last thing they read, and it is
   the easiest place to slip back into the kit's own vocabulary.

## Rules that hold throughout

- **Never ask the member to do architecture.** Taxonomy, page boundaries, file
  layout, frontmatter — yours, every time.
- **Plain words, and explain the ones that aren't.** The member owns what the
  brain is for, what it is built from, and how it behaves; the kit owns how it
  gets built, and the kit's vocabulary stays on the kit's side. Where a technical
  term genuinely helps, define it in-line the first time — educating is the goal,
  never dumbing down and never hiding the machine.
- **Fail loudly, never silently.** A source that could not be read is named in
  the log and counted in the summary. Never quietly skip.
- **Rights**: build only from material the member lawfully has, on their machine.
  Never remove DRM, never work around a paywall, attribute every chunk. All
  three are enforced in the arms, not by you — DRM'd files and DRM'd players are
  refused, paywalled extractions are quarantined outside `raw/`, and every
  `raw/` page carries its source and ingest date automatically. So say a refusal
  once, in a line, when it happens, and **never lecture the member, never ask
  them to confirm they have read a policy, and never raise the subject
  unprompted.**
- **`raw/` is immutable.** Ingested material is never edited, only distilled.
- **Built brains are never redistributed** — members rebuild from a prompt.
