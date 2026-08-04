# Brain Builder

Build a portable "brain" for your AI agent from any body of source material: YouTube channels, PDFs, books, web articles, podcasts.

A brain is a folder of markdown your agent navigates like a wiki. It answers questions like a subject-matter expert, cites its sources, and admits what it does not know. Build a subject brain (marketing, AI, your industry), a persona brain (a public figure's published thinking, answered in their voice), or a business brain (your own company's knowledge).

Made by Selr AI.

## Status

In build. When it ships, this repo carries the skill (`SKILL.md`), one paste-in install prompt (`SETUP-PROMPT.md`), and everything needed to build and attach brains. Until then it holds the design records and seed material the build starts from.

## What's here now

- `docs/spec.md` - the locked v1 build spec
- `docs/build-plan.md` - the ship list: deliverables and shipping constraints
- `docs/research/` - design records from the planning effort
- `docs/rights.md` - the content-rights stance the kit is built to
- `seed/` - prior assets the build reworks: the YouTube ingestion arm and an attach/detach prototype

Brains attach globally or per project in skills-directory harnesses (Claude Code, Codex); harnesses that read an instruction file instead (OpenClaw, Gemini) are global-only in v1.

## What you're responsible for

Brains are built locally, on your machine, from sources you have lawful access to, for your own use. The kit never ships content and your brains never leave your computer unless you move them. Details in `docs/rights.md`.
