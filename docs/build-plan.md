# Brain Builder — what has to exist to ship

Companion to [spec.md](spec.md). No schedule here — this is the work list and the shipping constraints, nothing else. Builds run as Claude sessions working from the spec; consult the `skill-creator` skill when authoring the skills. Seed material: the YouTube arm and toggle prototype under [`seed/`](../seed/).

## Deliverables

| # | Deliverable | Spec § | Notes |
|---|---|---|---|
| 1 | `brain-builder` skill (intake, gates, build phases, router generation) | §3, §5 | the core build |
| 2 | Blueprints directory: `subject.md`, `persona.md`, `business.md` | §4 | data files the builder enumerates; skeletons with commentary, never worked examples |
| 3 | Ingestion arms (YouTube seeded; local files, PDF/EPUB, web, Apple Podcasts/RSS new) + Scribe v2 fallback + dedup/number-verification/lint | §6 | rights enforcement in code: DRM refusal, paywall quarantine, per-chunk attribution |
| 4 | `brain-toggle` skill (global + project-scoped, symlink + pointer arms) | §7 | prototype seeded |
| 5 | `SETUP-PROMPT.md` + README rewritten for ship state | §8 | the one install path |
| 6 | Three demo brains rebuilt through the kit (AI expert, Marketing, Hormozi) + fail-question literals | §8 | rebuilding the Hormozi brain from a paste-in prompt doubles as the kit's acceptance test |
| 7 | `demos/` build prompts | §8 | nice-to-have, not a drop blocker |
| 8 | ~200-source scale test, findings to `docs/research/` | §6 | movable post-drop; the tin stays silent on size either way |

**Not cuttable**: the four router rule blocks, lint + number verification, the two gates, fail-loudly ingestion, the rights enforcement code. These are the difference between the kit and a transcript downloader. If anything else has to give, cut in this order: Spotify-via-RSS stretch → `demos/` prompts → scale test → pointer-arm harnesses go docs-only.

## Shipping constraints (from the drop decisions)

- Order of operations once built: **classroom page → announcement post → demo video last** — the video doubles as the Friday community call replay, and the Friday call (12:00 AEST) is the proper walkthrough.
- Both the Announcements post and the 🛠️ Weekly Builds classroom page carry the same single install prompt: "Clone https://github.com/luke-heka/brain-builder and follow SETUP-PROMPT.md". The replay page carries none.
- Post drafts + pre-post checklist are already written and parked at `~/selrai/active/brain-builder-drop/drop-week-content.md` (local) — sanity-check them against the shipped feature set before posting.
- Fail-question criteria are locked (verifiable corpus answer; brain-less Claude fails *confidently*; number / framework / voice coverage) — the literals get authored once the demo brains exist.
- Demo corpora are fixed: AI expert = Karpathy YouTube + blog; Marketing = mixed-source generic; Hormozi = the prototype's 30-video corpus. Built brains are never distributed (rights stance); members rebuild from prompts.
- Obsidian is the finish-phase graph viewer: a build ends by opening the brain there — installed first if missing, announced in one line, never a dependency and never a failed build — which closes the recommend-Obsidian question (see the `docs/spec.md` changelog).
