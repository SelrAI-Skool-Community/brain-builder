# Brain Builder — drop-week build plan

Companion to [spec.md](spec.md). Sized to land inside drop week (Mon 3 – Fri 7 Aug 2026): ship ASAP once built, proper walkthrough on the Friday community call (12:00 AEST, 7 Aug). Priority order across the week: **build → classroom page → announcement post → demo video last** (the video doubles as the Friday-call replay).

Builds run as Claude sessions working from spec.md; consult the `skill-creator` skill when authoring the skills. Seed material: the YouTube arm and toggle prototype under [`seed/`](../seed/).

## Deliverables

| # | Deliverable | Spec § | Notes |
|---|---|---|---|
| 1 | `brain-builder` skill (intake, gates, build phases, router generation) | §3, §5 | the core build |
| 2 | Blueprints directory: `subject.md`, `persona.md`, `business.md` | §4 | data files the builder enumerates |
| 3 | Ingestion arms + transcription fallback + dedup/verification/lint | §6 | YouTube arm seeded, everything else new |
| 4 | `brain-toggle` skill (global + project-scoped, symlink + pointer arms) | §7 | prototype seeded |
| 5 | `SETUP-PROMPT.md` + README rewrite for ship state | §8 | the one install path |
| 6 | Three demo brains rebuilt through the kit + fail-question literals | §8 | AI expert, Marketing, Hormozi |
| 7 | `demos/` build prompts | §8 | nice-to-have |
| 8 | ~200-source scale test, findings to `docs/research/` | §6 | movable post-drop |

## Day by day

### Tue 4 Aug — contracts and toggle
- Repo skeleton for ship state: `skills/`, `blueprints/`, `demos/` stubs.
- Write the three blueprint files (§4 table is the content spec; skeletons with commentary, never worked examples).
- Router generation template carrying all four rule blocks (navigation / stance / answering / citation) + per-kind variations.
- Port `brain-toggle` from seed: both arms, project-scoped mode, assisted split, move-not-duplicate.
- **Acceptance**: attach/detach round-trip on Claude Code, global and project-scoped; router fires from natural language in a fresh session.

### Wed 5 Aug — ingestion
- YouTube arm: port from seed, add self-update, archive file, empty-transcript detection, VTT dedup.
- New arms: local files, PDF/EPUB (PyMuPDF4LLM/EbookLib), web (trafilatura), Apple Podcasts + generic RSS resolver.
- ElevenLabs Scribe v2 fallback (transcript-first ordering, fail-loudly), corpus-level dedup, rights enforcement in code (DRM refusal, paywall quarantine, per-chunk attribution).
- **Acceptance**: each arm ingests one real sample end-to-end; a DRM'd and a paywalled source refuse loudly.

### Thu 6 Aug — the builder, end to end
- Builder skill: grilling-lite intake, source gate, plan gate with Scribe cost line, phased build (shared taxonomy pass → parallel section agents → first-class index generation → overlay when blueprinted), lint + number verification, Known gaps, finish = attach + member-question demo.
- **Acceptance test = rebuild the Hormozi brain from a paste-in prompt** and spot-check against the prototype's known-good answers (churn benchmark, margin floor, the out-of-corpus refusal).
- Evening: build the AI expert (Karpathy YouTube + blog) and Marketing (mixed-source) demo brains through the kit; kick off the ~200-source scale test overnight.

### Fri 7 Aug — ship and drop
- Author fail-question literals per demo brain (criteria locked: verifiable corpus answer; brain-less Claude fails *confidently*; number / framework / voice coverage).
- `SETUP-PROMPT.md` final pass; README rewritten for ship state; `demos/` prompts published.
- Scale-test findings → `docs/research/scale-test.md` (whatever state it reached).
- Record the demo video (last), publish classroom page + announcement post from the parked drafts, walkthrough on the Friday call.

## Cut lines, in order, if slipping

1. Spotify-via-RSS stretch (already a stretch in the spec).
2. `demos/` prompts (nice-to-have per the drop decision).
3. Scale test moves post-drop; the tin stays silent on size either way.
4. Pointer-arm harnesses go docs-only ("supported, one README line"), symlink arm ships tested.
5. The drop slips to Friday-with-the-call rather than earlier-in-week — the call was always the proper walkthrough.

**Not cuttable**: the four router rule blocks, lint + number verification, the two gates, fail-loudly ingestion, the rights enforcement code. These are the difference between the kit and a transcript downloader.
