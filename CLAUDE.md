# Brain Builder

A skill set that turns any body of source material into a portable **brain** — a standalone folder of markdown an agent navigates like a wiki. The locked build spec is `docs/spec.md`; the work list is `docs/build-plan.md`.

## Using the kit

If you have just cloned this repo to *use* Brain Builder, none of the sections below apply to you — follow [`SETUP-PROMPT.md`](SETUP-PROMPT.md). Bugs and requests go to this repo's **GitHub Issues**.

## Agent skills — maintainers only

The sections below configure agents working *on* the kit inside Selr's own tooling. They are not instructions to anyone else, and nothing in them is needed to build a brain.

### Issue tracker

For Selr maintainers, issues live in Selr's Linear (Core Builds team, Claude Brains Kit project). See `docs/agents/issue-tracker.md`. Everyone else: GitHub Issues on this repo.

### Triage labels

The five canonical triage labels, default names, as Core Builds team labels in Linear. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root (created lazily). See `docs/agents/domain.md`.
