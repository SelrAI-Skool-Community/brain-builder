---
name: topic-brain-builder
description: >
  One-touch builder that turns a topic into a reusable expert "brain." Name a
  topic and it autonomously finds the best YouTube content on it — well-known
  experts AND high-signal lesser-known voices (ranked by engagement and
  substance, NOT view count) — pulls the transcripts, extracts and collates the
  best information, and writes a portable brain skill anyone can load when they
  speak, write, or advise on that topic. Use when the user says "build a brain on
  X", "research the experts on Y", "what do the experts say about Z", "make me a
  brain about ...", "mine YouTube for the best on ...", or wants a durable,
  attributed knowledge base on a subject. Builds local files that ship anywhere.
metadata:
  type: builder
  version: 1.0.0
  built: "2026-05-28"
  engines: [yt-dlp, youtube-data-api, apify]
---

# Topic Brain Builder

Turn a topic into an expert brain in one touch. The user talks about a topic;
you find the best YouTube experts on it (popular AND hidden gems), collate the
best information, and leave behind a brain anyone can use later.

**Made by Selr AI.**

## The one rule that makes this elite

Selection is **NOT driven by view count.** A 200-view video from a sharp niche
operator with deep, specific content beats a 2-million-view video that's all
fluff. The scorer (`scripts/score.py`) leads on engagement rate + substance and
gives low-view / high-engagement videos a "hidden gem" boost, so lesser-known
experts surface alongside the famous ones. Never re-rank by raw views.

## Run it (6 phases — all automatic)

Set a working dir, e.g. `OUT=/tmp/brain-build` (any throwaway path).

### Phase 0 — Engine (auto)
```
python3 scripts/engine.py detect
```
Picks the best available engine and prints a one-line note:
- **yt-dlp** — the default. No key, no quota. If it's missing, `engine.py`
  installs it automatically (it tries brew, then pipx, then a user-scoped
  Python install, in order). This is automated — the user never touches a
  terminal and is never asked to install anything.
- **YouTube Data API v3 (your own Google)** — used automatically only if yt-dlp
  can't be installed AND the user has their own free key in any of `YT_API_KEY`,
  `YOUTUBE_API_KEY`, `GOOGLE_API_KEY`, `GCP_YOUTUBE_API_KEY`. Note for beginners:
  a "Google Workspace connected to Claude" does NOT by itself grant YouTube
  access — YouTube isn't a Workspace product. If someone wants the official
  Google path, they get a free YouTube Data API key from their Google Cloud
  console and set it as `YT_API_KEY`. But they almost never need to: yt-dlp
  already does everything with zero setup, so default to it and don't make a
  first-time user go get a key.
- **Apify** — used only if `APIFY_TOKEN` is set (richer comments).
- `gws` is NOT usable for YouTube — do not try it.
Tell the user which engine was chosen, in one line. If none is available, the
detect note says exactly what to do; do that yourself, don't bounce it back.

### Phase 1 — Discover (multi-angle)
```
python3 scripts/discover.py "<topic>" "$OUT" 15
```
Searches 8 angles (tutorial / mistakes / framework / how-to / explained /
advanced / strategy / plain), dedupes, and pulls full metadata. Writes
`candidates.json`. ~30-60s for the balanced default.

### Phase 2 — Score (the not-just-views engine)
```
python3 scripts/score.py "$OUT" 28
```
Writes `selected.json` (~25-30 videos, max 3 per channel, a new/evergreen mix,
hidden gems boosted) plus the full ranked table and a plain-English reason each
video made the cut.

### Phase 3 — Transcripts
```
python3 scripts/extract.py "$OUT"
```
Downloads + cleans English captions for the selected videos into
`$OUT/transcripts/<id>.txt`. Some videos have no captions — that's fine, the
script skips them and records it.

### Phase 4 — Scaffold the brain
```
python3 scripts/build_brain.py "$OUT" "<topic>"
```
Creates `~/.claude/skills/brain-<slug>/` with SKILL.md + reference stubs +
`sources/` (transcripts copied in) + `sources-index.md` (the scored table) +
CHANGELOG. Prints the brain dir + the sections you fill next.

### Phase 4b — FILL the brain (this is your job, not a script)
Read every `sources/*.txt` transcript in the new brain, then write real content
into the stubs (replace every `<!-- FILL -->`):
- **`references/synthesis.md`** — cluster the material into themes. Under each:
  the point, which experts back it, and a concrete number/example. Mark
  consensus vs contested.
- **`references/quote-library.md`** — verbatim golden quotes, each attributed:
  `> "quote" — Creator, *Video Title*`.
- **`references/experts.md`** — per creator: name, popular or hidden-gem, their
  angle, what they uniquely add.
- **`SKILL.md`** — fill the "What the experts agree on", "Named frameworks &
  methods", and "Contrarian / disputed takes" sections.
Be specific and attributed. No invented facts, no fluff. If a transcript is thin,
skip it rather than padding.

### Phase 5 — Report
One short summary: topic, # videos mined, popular-vs-hidden-gem split, # quotes,
where the brain lives, and how to use it ("just ask about <topic> in a new chat,
or load `brain-<slug>`"). Never end with a human-escalation line — if something
failed, you already retried and self-healed.

## First run for a brand-new user — keep it fast

If this is someone's first time, run at **fast depth (~12 videos)** so they get a
finished brain in ~3 minutes and see it work, then offer to go deeper. Don't make
a first-timer wait 10 minutes on a 50-video run.

## Self-heal rules

- yt-dlp missing → `engine.py` installs it automatically (brew / winget / pipx /
  pip — covers Mac, Windows, Linux), then continue.
- A video errors (private/region-locked/no captions) → skip it, keep going.
- `discover.py` exits with code 2 + `too_thin` → the topic phrasing was too narrow.
  Don't build an empty brain. Re-run once with a broader phrasing or a higher
  per-angle count; if still thin, tell the user plainly to broaden the topic.
- yt-dlp rate-limited (many people on one network, or repeated runs) → wait a
  moment and retry; transcripts can also be fetched one at a time more slowly.
- Never abort the whole run because one step had an issue. Never ask the user to
  fix something you can fix.

## Depth presets

Default is balanced (~28 videos). For a fast first pass use ~12
(`score.py "$OUT" 12`); for exhaustive use ~50 and raise `discover.py` per-angle
to 25. More videos = longer transcript synthesis.

## What you get

A `brain-<topic>` skill: attributed synthesis + a quote library + an experts map
+ the raw transcripts. Portable — works on any machine, no keys, no services.
