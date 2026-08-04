---
name: brain-toggle
description: "Turn a knowledge brain on or off for this machine's agent harnesses. Use when the user says 'turn on my <name> brain', 'attach the <name> brain', 'switch off <name>', 'detach <name>', 'which brains do I have', 'what's attached', or wants a brain on only inside one project."
---

# Brain Toggle

Attaches and detaches **brains** — standalone folders of markdown — to the agent
harnesses on this machine. An attached brain costs roughly its router's
`description` in idle context; the body only loads when the router fires.

Brains live anywhere; the default is `~/brains/<slug>/`. Every operation below
runs through one script:

```bash
python3 skills/brain-toggle/scripts/toggle.py <command> [options]
```

Run it with no arguments for the full option list.

## The two arms

| Harness kind | Mechanism | Scopes |
|---|---|---|
| Skills directory — Claude Code, Claude Agent SDK, Codex, any SKILL.md-standard harness | symlink the brain folder in | global + project |
| Instruction file — OpenClaw, Gemini, Hermes | a delimited pointer block | global only in v1 |

Neither needs a restart.

## Attaching

**Global is the default.** Unless the member asks for a project, attach globally
and say nothing about scope.

```bash
python3 .../toggle.py attach ~/brains/hormozi
```

The script prints the directory it is targeting, then what it linked. Report
both back, plus any `warning:` line verbatim — a warning means the brain's
router records a root the brain no longer sits at, and the fix is the
`gen_router.py ... --root ...` command the warning prints.

**Project-scoped is opt-in**, for "only in this project" / "just for this repo":

```bash
python3 .../toggle.py attach ~/brains/acme-business --scope project --cwd .
```

The target resolves to the **git root** when inside a repo, else the current
directory. **State the resolved path before linking** — the script prints it as
`target: ...`; put it in front of the member.

Scoping is additive, never shadowing: skills directories load together, so a
project attachment stacks on top of whatever is global.

### Already attached somewhere else

A project attach for a brain that is already global exits **3** and does
nothing. Do not retry blindly. Offer the choice:

> `hormozi` is already on globally. Move it into this project, or leave it
> global and on everywhere?

Re-run with `--move` only if they choose to move. Never end up with the same
brain attached twice — that loads two copies of the router.

## Detaching

```bash
python3 .../toggle.py detach hormozi                      # global
python3 .../toggle.py detach acme-business --scope project --cwd .
```

Detach removes a symlink and nothing else; the brain folder is untouched. If
something other than a link sits at the target, the script refuses and says so
— relay that rather than deleting anything by hand. Confirm first when
detaching more than one brain at once.

## Listing

```bash
python3 .../toggle.py list --cwd . --brains-dir ~/brains
```

Reports every scope it scanned, what is attached in each, and — with
`--brains-dir` — the brains that are currently off. `(BROKEN: target is gone)`
means the brain was moved or deleted out from under the link.

## Assisted split — "brain X in this terminal, brain Y in another"

Asks shaped like *"I want hormozi in my content repo and the business brain in
the client repo"* are asking for the project-scoped split. Recommend it, then
set it up in one pass:

1. **Propose the mapping** — one line per brain: brain → project directory.
   Get a yes before touching anything.
2. **Detach the involved globals** (`detach <slug>`), so nothing is duplicated.
3. **Attach each brain into its project**, running the command from that
   directory (or passing `--cwd`), and state each resolved target.
4. **Confirm per directory**: name each project and the brain now on there.

That is the whole feature — no config file, no profiles, no state of its own.

## Instruction-file harnesses (pointer arm)

For harnesses that read an instruction file rather than a skills directory.
Ask the member for the file's path if it is not obvious — the common ones are
`~/.gemini/GEMINI.md` and the harness's global `AGENTS.md`.

**Show the diff before the first write:**

```bash
python3 .../toggle.py pointer-diff ~/.gemini/GEMINI.md ~/brains/hormozi
python3 .../toggle.py pointer-add  ~/.gemini/GEMINI.md ~/brains/hormozi
python3 .../toggle.py pointer-remove ~/.gemini/GEMINI.md hormozi
```

What goes in is a delimited block — three lines, appended:

```
<!-- brain: hormozi -->
The hormozi brain is at /Users/.../brains/hormozi. Start at its index.md and follow the links; never bulk-load it.
<!-- /brain: hormozi -->
```

Rules, non-negotiable:

- **Never paste brain content into an instruction file.** Instruction files
  inject whole on every turn; a brain in one is a permanent context bill. The
  block points, and that is all.
- **Never reformat what the member wrote.** The block is appended, or replaced
  between its own delimiters. Removal restores the file byte for byte.
- Instruction-file harnesses are **global-only in v1**. Project-scoped pointer
  blocks are not built.

## Recipes

- **Always-on brains stay global** — the reference brain you want on everywhere.
- **Persona and business brains attach to their project** — a client's business
  brain belongs in that client's repo, not on every session on the machine.
- **One brain per working directory** when two sessions need different brains.
  Two concurrent sessions in the *same* directory cannot have different
  project-scoped brains — the skills directory is a property of the directory,
  not of the session. Give each brain its own working directory.

## Before attaching an unfamiliar brain

`attach` checks the folder has the mandatory minimum (`SKILL.md`, `index.md`,
`wiki/`) and refuses otherwise. For the full contract check, run the builder's
linter first:

```bash
python3 skills/brain-builder/scripts/lint.py ~/brains/hormozi
```
