# Brain Builder — v1 build spec

**Status: locked.** This document folds every decision from the planning effort (the "Claude Brains Kit" wayfinder map, Selr Linear CORE-121) into one build spec. It locks on merge; amendments after that get a changelog entry at the bottom, not silent edits. The companion [build-plan.md](build-plan.md) sizes the build to land inside drop week.

Linear references (CORE-nnn) are provenance for the Selr team; the substance is all here.

---

## 1. What v1 is

A skill set that turns any body of source material — YouTube channels, PDFs, books, web articles, podcasts, local files — into a portable **brain**: a standalone folder of markdown an agent navigates like a wiki, which answers as a subject-matter expert, cites its sources, and admits what it doesn't know.

Three shipped components:

1. **`brain-builder`** — the builder skill. Natural-language intake, proposes sources, builds the brain.
2. **`brain-toggle`** — the attach/detach skill. Connects brains to the member's harness(es).
3. **Blueprints** — three shipped brain kinds (Subject, Persona, Business) as data files the builder reads.

Zero infrastructure: no RAG, no embeddings, no database, no server. Files only. (CORE-125)

**Ubiquitous language** (CORE-139): a **brain** is an artefact Claude pulls from to change its knowledge, behaviour, and response style. A **kind** is a blueprint, not a type — the taxonomy is open. An **overlay** is a named optional folder with a defined contract (`persona/`, `standing/`). **Attach/detach** connect a brain to a harness. **Stacking** is multiple brains attached at once.

## 2. A brain on disk (CORE-125)

Brains live anywhere on disk; default `~/brains/<slug>/`. Every brain has the same top-level contract:

```
<slug>/
  SKILL.md        # the generated router — the brain's entire interface (§3)
  index.md        # the map: one-liners carrying real numbers, + ## Known gaps (required)
  wiki/           # the synthesized knowledge base; interior taxonomy free per brain
  raw/            # immutable ingested source material, fenced, kept in-tree
  log.md          # build + write-back timeline
  CHANGELOG.md
  persona/        # optional overlay: voice.md + exemplars.md
  standing/       # optional overlay: standing facts and policies
```

- **Fixed skeleton, free interior.** `SKILL.md` + `index.md` + `wiki/` are the mandatory minimum for a folder to be a brain; `raw/`, `log.md`, `CHANGELOG.md` lint-warn rather than lint-fail. Inside `wiki/` the builder decides the taxonomy per brain at build time. Lint ignores folders it doesn't recognise — a brain carrying an unimagined shape is still a valid brain. (CORE-125, CORE-127)
- **OKF conformance.** Pages carry OKF-conformant frontmatter (`type` field; reserved files `index.md`/`log.md`), checkable with Google's stdlib validator. Near-free portability + marketing label; the operating machinery is the Karpathy wiki pattern (ingest / query / lint, raw/compiled split).
- **`raw/` is immutable, fenced, in-tree.** Kept for provenance, citations, and re-distillation. Fencing = router instruction + exclusion from the index. Supports the rights stance (attribute every chunk — [rights.md](rights.md)).
- **Retrieval is agentic file navigation only.** Start at `index.md`, follow links, never bulk-load folders. No RAG. File-navigation ceiling (~hundreds to 5,000 pages) is far above any community brain.
- **Freshness frontmatter** (business kind, available to all): `as_of` + `volatility: fast|slow|stable` + `canonical:` (where the live truth lives). (CORE-140)

## 3. The router contract — `SKILL.md` (CORE-127, CORE-128, CORE-140, CORE-141)

The generated `SKILL.md` at the top of each brain **is the consumption interface**. There is no query skill, no wrapper, no config file. Its description fires it from natural language; it records the brain's absolute root at attach time and works from any directory. It is self-contained (a brain folder works standing alone on any machine) and regenerable (a kit command rewrites the router when the kit improves).

The router carries **both halves** of the contract — the prototype proved navigation alone routes perfectly and still feels wrong (CORE-128):

**Navigation rules**
- Start at `index.md`, follow links; never glob or bulk-load. Put a short "start at index.md, never glob the tree" clause **in the frontmatter description itself** — two stacked-test sessions globbed before the router body was in context (CORE-141).
- Page budget: 2–3 wiki pages per question, **per brain** in stacked sessions. Restated in the answering rules (it was ignored where it sat only in navigation).
- `index.md` loads once per session; direct routing allowed after (CORE-140).
- `raw/` is fenced: never opened except for a verbatim quote or an explicit provenance question.

**Stance rules**
- **Commit to a stance and hold it.** Advisor stance is the default; persona stance when the brain declares one. Extensible — never written as a cap of two.
- **No middleman.** Never relay a named third party at arm's length. "Here's what the brain says" is banned in every stance. The one sanctioned exception is flagging a corpus boundary, and it costs a sentence.
- **One voice per session** (stacking): at most one persona drives voice; while it does, all other attached brains are silent fact sources. Non-persona stances must be advisor-compatible. (CORE-141)

**Answering rules**
- Lead with the answer. Never narrate retrieval ("Loading…", "Read five pages…").
- Answer in your own voice, second person, flat certainty on the brain's own facts.
- In-domain gaps: state plainly via `## Known gaps` — refusal fires **only** when the question is inside the domain but uncovered. Out-of-domain questions are answered normally from general knowledge, no disclaimer.
- Fast-volatility facts are answered with their as-of date attached in the same breath — the number stays exact, the date is the honesty (business kind).

**Citation rules** — placement and weight are separate specifications (CORE-128):
- **Exactly one closing `Sources` block** of brain-relative paths (`wiki/<page>.md`) — the file you'd edit to fix an error. Inline markers permitted but minimal.
- In stacked sessions, prefix paths with the brain slug: `<slug>/wiki/<page>.md` (CORE-141).
- Business kind: the Sources block is **conditional** — only on answers carrying numbers/prices/dates/commitments — annotated `(as of …; canonical …)` (CORE-140, a per-kind amendment to the always-on rule).
- Never cite `raw/` except for verbatim quotes; the wiki page's frontmatter is the chain back to source.
- Out-of-domain answers carry no Sources block; pages created by write-back are marked derived-from-conversation so a Sources block never implies grounding that doesn't exist.

**Conflict rule** (stacking, CORE-141): a business brain's facts and standing policies outrank subject-brain guidance for outward-facing work; conflicts are surfaced, never silently resolved.

**Write-back** (CORE-127, Karpathy verbatim): good answers file back into the wiki as new pages **during** the conversation — no staging, no approval gate, no batch review. Each write is announced in-line and appended to `log.md`; undo is git. Derived-from-conversation marking keeps citations honest.

## 4. Brain kinds — three blueprints (CORE-139)

Kinds are **blueprints, not types**: one markdown file each in the builder's blueprints directory, blessed by default, custom shapes honoured on explicit opt-out, never advertised, never lint-enforced. All three ship in v1.

| | **Subject** | **Persona** | **Business** |
|---|---|---|---|
| Wiki organised | by concept | by concept (subject core) | by entity and process (offers, clients, pricing, how-we-do-X) |
| Overlays | none | `persona/` — `voice.md` + `exemplars.md`, loaded whole, never merged with facts | optional `standing/` — standing facts and policies, loaded whole, **unfenced** (routed like wiki pages) |
| Stance | advisor | **speaks as the person** — the only stance-changing kind | advisor — Claude speaks as itself, outside the business: "you/the business offers X", never "we" |
| Signature behaviour | — | anti-caricature section (mandatory — it's a hallucination brake, CORE-128) + calibration question with a known answer | **write-back expected routinely** (the staleness-prone kind); freshness frontmatter; **source-authority ranking pass + explicit contradiction flags at build time** (CORE-140: a business corpus contradicts itself — adjudicating which documents to distrust is the kind's first job); confidentiality rules in the router (local-only; one client's details never reach another client's documents or outward-facing drafts unasked) |

- **Persona is ONE composite blueprint**: subject core + voice on top — the shape the prototype validated. Voice fidelity: exemplars do the heavy lifting (10–20 verbatim excerpts chosen for range, including short-form register), `voice.md` stays a thin list of observable rules. Voice-only is reachable only via the warned custom opt-out ("no corpus of its own; it will lean on Claude's own knowledge and live research").
- **Stacking**: any kinds stack, unlimited attach; one persona max drives voice. Validated end-to-end at n=2 with zero misroutes and no orchestration layer (CORE-141). Idle cost ≈ 140 tokens per attached brain.

## 5. The builder skill (CORE-136)

Natural-language skill plus a slash command; one paste-in prompt is a complete invocation.

- **Intake = grilling-lite**: interview to *shared understanding*, not question coverage. Four things must be understood (from the member or the builder's own research): what the brain is about → selects the blueprint; what it's built from; where the sources come from; what the member wants to ask it (feeds calibration + Known gaps). Full mind-dump ⇒ zero questions. Research instead of asking anything look-up-able. The member is never asked to do architecture.
- **Shape selection**: the builder enumerates the **blueprints directory** at runtime (adding a kind = adding a file), suggests one from what the member said, explains it, confirms in a line. One blueprint per brain; nothing merges at build time — multi-kind behaviour is stacking at attach time.
- **Two conversational gates**: (1) proposed source list, grouped by platform with counts and one-line reasons, edited by talking until approved; (2) plan gate — shape + slug (derived, stated as "→ `~/brains/<slug>/`", overridable in passing, never a question) + source count + estimated transcription hours/cost before ingest. One approval, then build.
- **Build**: phase-level narration with counts (ingest → taxonomy → pages → lint → router). A **shared taxonomy pass runs before parallel section agents** (CORE-128). Failures never halt: dead transcripts/paywalls/empty captions log to `log.md`, one summary line at the end. Stop only if the whole corpus fails.
- **Self-check**: lint + number verification close every build; leftovers become `## Known gaps`, not build errors. `index.md` generation is a first-class step — one-liners carry the actual numbers, which is what makes routing accurate.
- **Finish = proof**: attach via the toggle skill, then demo the brain with one of the member's own questions.

## 6. Ingestion pipeline (CORE-124, CORE-126, CORE-128)

**v1 sources**: local files (md/txt/csv/json/docx) · PDFs/EPUB (PyMuPDF4LLM / EbookLib) · bulk YouTube (yt-dlp as a library: self-update, archive file, empty-transcript detection) · web articles (trafilatura) · **Apple Podcasts + generic RSS** (iTunes Lookup API → `feedUrl`; check `<podcast:transcript>`, else transcribe the enclosure). Spotify-via-RSS is a stretch goal (resolve to RSS only; never touch the DRM'd player; fail loudly on exclusives).

**Deferred**: Instagram, TikTok, Vimeo, X, Facebook, LinkedIn, Spotify music, audio-file OCR. Two subsystems, not one: yt-dlp for anything video-shaped + a small RSS/podcast resolver, both feeding one transcription fallback.

**Ordering per source**: platform/publisher transcript → transcription fallback → **fail loudly**. Never silently skip.

**Transcription engine: ElevenLabs Scribe v2** ($0.22/hr, 2.2% WER, diarization built in, 10-hour files in one call). Whisper-family engines are rejected for the disqualifying failure mode: fluent invented sentences during silences on long-form audio — poison for a verbatim persona corpus. Groq stays documented as an explicit "rough indexing, never quote it" cheap mode. Cost surfaces once, at the plan gate.

**Evidence-backed pipeline requirements** (all from the prototype, CORE-128):
- **VTT/caption dedup** — rolling captions inflate word count ~3–4×.
- **Corpus-level dedup** — compilations repeat other sources near-verbatim.
- **Number-verification pass** — ASR corrupts exactly the names and figures that matter; cross-check figures against surrounding arithmetic before they become citable wiki facts.
- **Lint** — link check (8/191 dangled in the prototype, clustered on the most-reached-for concepts), frontmatter check, skeleton check.
- **Per-page provenance context** — pages note the scale/context of their data, not just citations.

**Rights enforcement lives in code, prose lives in docs** ([rights.md](rights.md)): refuse DRM, quarantine paywall stubs, attribute every chunk. The model never nags mid-run or asks the member to confirm they've read the policy.

## 7. Attach / detach — the toggle skill (CORE-125, CORE-127, CORE-145)

Natural-language triggered ("turn on my hormozi brain"). Two mechanical arms:

1. **Symlink into a skills directory** — Claude Code (`~/.claude/skills/`), Claude Agent SDK, Codex (`~/.codex/skills/`), and the SKILL.md open standard. Idle cost ≈ the router description only; no restart.
2. **Pointer block in the harness's instruction file** — a delimited, reversible `<!-- brain: slug -->` block appended to e.g. OpenClaw/Gemini instruction files; never reformats member-authored content; diff shown on first use. Never paste brain content into instruction files.

**Scoping** (CORE-145): **global attach is the default; project-scoped attach ships as an opt-in second mode** — same one-line operation, the symlink just points at the project's skills dir instead of the user-level one. Semantics are additive, never shadowing (skills dirs load together; shadowing isn't buildable). Recipe: keep always-on brains global; attach persona/business brains to their project. Details:

- Project target resolves to the **git root** when inside a repo, else cwd; the skill states the resolved path before linking.
- Attaching an already-global brain to a project offers to **move** it, never silently duplicates the router.
- **Assisted split**: asks shaped like "brain X in this terminal, brain Y in another" get the project-scoped split recommended and set up — propose the mapping, detach the involved globals, link each into its project, confirm per directory. Deliberately lean: a short router section, not a subsystem.
- Instruction-file harnesses stay global-only in v1 (one README line says so). Unservable edge, stated honestly: two concurrent sessions in the *same directory* wanting different brains — give each brain its own working directory.

Any number of brains attach at once; clashes are the member's problem (mitigated by the stacking contract, §3).

## 8. Distribution (CORE-129, CORE-142)

- **Name: Brain Builder.** Public repo **`luke-heka/brain-builder`** (this repo). Gating consciously deferred; ship open.
- **Install: one paste-in prompt** — "Clone https://github.com/luke-heka/brain-builder and follow SETUP-PROMPT.md" — carried by the Skool announcement post and the Weekly Builds classroom page.
- Demo build prompts published under `demos/` as worked examples of the builder intake (nice-to-have, not a drop blocker). **Built brains are never distributed** (rights stance); members rebuild from prompts.
- The internal gbrain MCP push from the seed skill is stripped — zero-infra, no Selr infrastructure in the kit.
- Drop-week content (posts, demo video, fail questions) is decided and drafted, parked until the build lands; it fires per the build plan.

## 9. Explicitly open after v1

Carried as open fog on the planning map, deliberately not specified here:

- **Incremental ingest** of new source material after first build (write-back is settled; re-ingestion is not).
- **Whether Obsidian is recommended** as part of the kit (its graph view is a demo visual; the recommendation question stays open).
- **A general quality bar / evaluation** for subject-matter brain answers (voice calibration and demo fail-questions are settled; the general equivalent isn't).
- **Listing/inspecting installed brains** (storage, switching, naming are settled).
- Deferred sources (§6), and any hosted/SaaS brain product (out of scope entirely — the kit runs inside members' own harnesses).

---

*Changelog: none — locked as written.*
