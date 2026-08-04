# Brain Builder

Turn any body of source material — YouTube channels, PDFs, books, web articles,
podcasts, your own files — into a **brain**: a standalone folder of markdown
your agent navigates like a wiki, answers from as a subject-matter expert, cites
the page you would edit to fix an error, and admits what it does not know.

Zero infrastructure. No RAG, no embeddings, no database, no server. Files only.

Made by Selr AI.

## Install

Paste this into Claude Code (or Codex, or any coding agent):

> Clone https://github.com/luke-heka/brain-builder and follow SETUP-PROMPT.md

That is the whole install. The agent clones the repo, links the two skills into
your harness, verifies the machinery against a fixture brain without touching
your real profile, and tells you it is ready. No dependencies, no API key, no
network beyond the clone itself. `SETUP-PROMPT.md` is the complete path if you
would rather read it first.

## What a brain is

A folder on disk, at `~/brains/<slug>/` by default:

```
<slug>/
  SKILL.md      the generated router — the brain's entire interface
  index.md      the map: one-liners carrying real numbers, + ## Known gaps
  wiki/         the synthesized knowledge; taxonomy chosen per brain
  raw/          the ingested source material, immutable, fenced, kept in-tree
  log.md        build + write-back timeline
  CHANGELOG.md
```

`SKILL.md` is the whole consumption interface — there is no query skill, no
wrapper, no config file. Its description fires it from natural language, and it
carries both halves of the contract: how to navigate (start at `index.md`,
follow links, never bulk-load, 2–3 pages per question) and how to speak (lead
with the answer, hold a stance, one closing `Sources` block, refuse honestly
inside the domain and answer normally outside it).

Retrieval is an agent reading files. That ceiling sits in the thousands of
pages, far above any brain you will build, and it means a brain works standing
alone on any machine with nothing installed.

Attached brains cost roughly their router's description in idle context — about
140 tokens. The body only loads when the router fires.

## The three components

**`brain-builder`** — the builder skill. One paste-in prompt is a complete
invocation. It interviews you to shared understanding rather than question
coverage (a full mind-dump earns zero questions), proposes the source list
grouped by platform for you to edit by talking, states the plan and the
transcription cost once, then builds: ingest → taxonomy → pages → router →
lint. It finishes by attaching the brain and answering one of your own questions
with it. You are never asked to do architecture.

**`brain-toggle`** — the attach/detach skill. "Turn on my hormozi brain."
Symlinks a brain into a skills directory (Claude Code, Claude Agent SDK, Codex,
any SKILL.md-standard harness), globally by default or scoped to one project as
an opt-in. Any number of brains attach at once.

**Blueprints** — three shipped brain kinds, as data files the builder reads at
runtime:

| | Subject | Persona | Business |
|---|---|---|---|
| Wiki organised by | concept | concept | entity and process |
| Overlay | none | `persona/` — voice + exemplars | optional `standing/` |
| Stance | advisor | speaks as the person | advisor, from outside the business |

One blueprint per brain. Two shapes means two brains, stacked at attach time —
and stacking is where a business brain's facts and a subject brain's guidance
work together, with at most one persona driving voice.

## Ingestion

One arm per source family, all returning the same manifest: local files
(md/txt/csv/json/docx) · PDFs and EPUBs · YouTube channels, playlists and
searches · web articles · Apple Podcasts and any RSS feed. Where a publisher
ships no transcript, audio falls back to transcription (ElevenLabs Scribe v2,
$0.22/hour, priced once at the plan gate before anything is spent).

Sources fail **loudly, per source**. A dead transcript, a paywalled article, a
DRM-refused book, a missing library — each is named on its record and in
`log.md`, and the build carries on. Nothing is ever silently skipped. Only a
corpus where *nothing* came out stops a build, which is the one thing that
should stop one.

Optional per-arm dependencies (`yt-dlp`, `pymupdf4llm`, `EbookLib`,
`trafilatura`) install only when you use that arm, and the arm prints the one
line that fixes it. A brain built from your own markdown needs none of them.

## Harnesses and scope

Brains attach globally or per project in skills-directory harnesses (Claude
Code, Claude Agent SDK, Codex). Harnesses that read an instruction file instead
(OpenClaw, Gemini) get a reversible pointer block, and are **global-only in
v1**.

Scoping is additive, never shadowing: a project attachment stacks on top of
whatever is global. The recipe is to keep always-on brains global and attach
persona and business brains to their project.

One edge this does not serve: two concurrent sessions in the *same* directory
wanting different project-scoped brains. The skills directory is a property of
the directory, not of the session, so there is no way to split them. Give each
brain its own working directory.

## Demos

`demos/` carries three worked build prompts — an AI expert brain, a marketing
brain, and the Hormozi persona brain — each a complete paste-in invocation of
the builder, each with the fail questions that prove the built brain knows
something a brain-less agent gets confidently wrong. Built brains are never
distributed; you rebuild from the prompt.

## What you're responsible for

Brains are built locally, on your machine, from sources you have lawful access
to, for your own use — the kit never ships content, refuses DRM, quarantines
paywalls, and attributes every chunk. Details in [`docs/rights.md`](docs/rights.md).

## What's in this repo

- [`SETUP-PROMPT.md`](SETUP-PROMPT.md) — the install path, start to finish
- `skills/brain-builder/` — the builder skill, its scripts and blueprints
- `skills/brain-toggle/` — the attach/detach skill
- [`demos/`](demos/) — worked build prompts and their fail questions
- `docs/spec.md` — the locked v1 build spec
- `docs/rights.md` — the content-rights stance the kit is built to
- `docs/research/` — design records from the planning effort
- `seed/` — the prior assets the build started from, kept as history
- `tests/` — the suite, stdlib-only: `python3 -m unittest discover tests`
