# Prior art: how people build "brains" for LLM agents

Migrated from planning ticket CORE-123 (resolved 2026-07-31).

Surveyed seven shapes: Obsidian wiki vaults, the Karpathy LLM-wiki, skill-native progressive disclosure (SKILL.md + references/), NotebookLM grounding, local RAG/embeddings, agent memory systems (mem0/Letta/Zep/basic-memory), and persona-emulation builds.

## Shortlist

1. **Karpathy LLM-wiki packaged as a skill** (`raw/` + `wiki/` + `index.md` + `log.md`; ingest/query/lint operations). For: zero infra, zero keys, pure markdown, portable to any harness, the most-validated pattern of 2026 (Karpathy's own wikis run 100+ articles / ~400k words), and the lint op directly targets the staleness failure everyone else reports. Against: synthesis quality needs human supervision on early ingests; wants semantic help somewhere past a few hundred to ~5,000 pages.
2. **Skill-native progressive disclosure** (SKILL.md router + references/ corpus, possibly OKF-spec conformant). For: the harness's own documented mechanism (~100 tokens until triggered, one git clone, nothing to run). Against: measured in the wild (SkillReducer, arXiv), lazy loading silently collapses into context stuffing unless the SKILL.md body is disciplined about not instructing broad reads.
3. **Distilled voice artifact for personas** (corpus to a generated voice/principles doc loaded whole, raw corpus kept as citable archive). For: the only shape with converging independent evidence it beats both raw dumping and RAG for persona fidelity; multiple sources report RAG-over-raw-corpus actively hurts voice. Against: lossy one-way distillation (growth = rebuild), and it answers voice only; a facts/recall layer must sit beside it.

## Cross-cutting findings

- **Facts/recall and voice/judgement are orthogonal axes.** Retrieval hygiene wins the first; distillation wins the second; a brain is usually asked for both, so the winning design is likely a hybrid (wiki for facts + distilled voice.md for persona).
- **Every RAG/embeddings option violates zero-infra somewhere** (Docker/Qdrant/Postgres/Neo4j/OpenAI keys). Anthropic's own Claude Code team dropped RAG for agentic search ("agentic search outperformed RAG by a lot"). NotebookLM is ruled out entirely: no public API, can't be a skill.
- **File-navigation ceiling converges at a few hundred to ~5,000 notes** from three independent sources, comfortably above any one-week community brain.
- **Ship zero-infra and infra-heavy as separate products.** coleam00's second-brain repos already split exactly this way; copy the split, don't resolve it.
- Portability model to copy: agent-agnostic markdown core + per-harness hook dirs (`.claude/`, `.codex/`, `.gemini/`; see breferrari/obsidian-mind).

Headline repos: Ar9av/obsidian-wiki (manifest-tracked delta re-ingest, confidence tags), mattjoyce/okf-skill (portable spec + validator), coleam00/second-brain-skills, ammonhaggerty/my-digital-twin (distill-then-load-whole persona precedent).
