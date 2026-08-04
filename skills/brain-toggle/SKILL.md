---
name: brain-toggle
description: "Turn a knowledge brain on or off for this machine's agent harnesses. Use when the user says 'turn on my <name> brain', 'attach the <name> brain', 'switch off <name>', 'detach <name>', 'what's attached where', or wants a brain on only inside one project."
---

# Brain Toggle

Turns a **brain** — a standalone folder of markdown pages — on and off for the AI
tools installed on this machine. A brain that is on costs roughly its router's
`description` in idle context — that is, only the one-line summary on its front
page sits there; the pages themselves load when a question actually reaches for
one.

Brains live anywhere; the default is `~/brains/<slug>/`. Every operation below
runs through one script, `scripts/toggle.py`, which **sits next to this file**.

`scripts/…` below means *this skill directory*, not the member's working
directory — you are running inside their project, not inside the kit. Resolve it
once at the start and use the absolute path from then on:

```bash
TOGGLE=~/.claude/skills/brain-toggle/scripts/toggle.py   # or wherever this skill was installed
python3 "$TOGGLE"                                        # no arguments: the full option list
```

## How to say it

The member says which brain and where. The mechanics are yours, and the words
that reach them are plain. **Never hide a technical detail — explain it.** Any
technical word you do use gets a short explanation the first time it appears, so
the member finishes the exchange understanding the machine rather than trusting
it blindly.

This applies to what you **ask** as much as what you report: *"which brain, and
on everywhere or only in this project?"*, never *"at which scope and harness?"*

The right-hand column is **register, not a script** — match its plainness and its
level of explanation, then use the real names and paths in front of you. Never
emit these lines verbatim.

| Not this | This |
|---|---|
| "attached to your Claude Code harness" | "turned on for Claude Code — the tool you're using right now" |
| "attached globally" | "on everywhere, in every project" |
| "attached at project scope" | "on only inside `~/work/acme`; other projects won't see it" |
| "symlinked into the skills directory" | "linked in — the brain stays where it is at `~/brains/hormozi` and Claude follows a pointer to it, so nothing is copied or moved" |
| "it costs its router description in idle context" | "it sits idle costing one line of summary; the pages only load when a question needs them" |
| "run the linter first" | "check it over first — that every page carries the details it needs and every link goes somewhere real" |
| "the link is broken" | "the link points at a folder that isn't there any more — the brain was moved or deleted" |

**Hold back talk of other tools unless it is genuinely the member's problem.**
Most members only ever use Claude Code, and "harness" is a word they have no
reason to know — never use it with them. Name a second tool only when one of
these is true:

- they ask about Codex, Gemini or another tool by name;
- the brain really is on in more than one and the answer would be wrong without
  saying so — a `list` covering two of them, or a detach that removes it from
  both;
- `--skills-dir` or an instruction file is in play, which only ever happens
  because they asked for it.

When it does have to appear, spend the words on it once: *"it's on for both
Claude Code and Codex — two separate tools on this machine, each with its own
switch, so turning it off in one leaves the other alone."* Otherwise say Claude
Code, or say nothing about tools at all.

The rest of this file is written in mechanics vocabulary — scope, harness,
symlink, router — because that is the vocabulary you need to operate the script.
**None of it is cleared for use with the member.** Where a section below quotes a
line to say out loud, it has already been translated; everything else gets
translated by you on the way out, under the rules above.

## The two arms

| Harness kind | Mechanism | Scopes |
|---|---|---|
| Skills directory — Claude Code, Claude Agent SDK, Codex, any SKILL.md-standard harness | symlink the brain folder in | global + project |
| Instruction file — OpenClaw, Gemini | a delimited pointer block | global only in v1 |

Neither needs a restart. `--harness claude-code` (the default) and
`--harness codex` are the two named ones; the Claude Agent SDK reads the same
directories as Claude Code, so it is `claude-code` too. **Any other
SKILL.md-standard harness: pass `--skills-dir <its skills directory>`** and the
same attach/detach/list commands work unchanged.

## Attaching

**Global is the default.** Unless the member asks for a project, attach globally
and say nothing about scope.

```bash
python3 "$TOGGLE" attach ~/brains/hormozi
```

The script prints the directory it is targeting, then what it linked. Report
both back — in member words: which brain is now on, and where it will apply. Any
`warning:` line goes back verbatim, with one sentence of translation: a warning
means the brain's front page still records the folder it used to live in, so it
was moved after it was built, and the fix is the `gen_router.py ... --root ...`
command the warning prints.

**Project-scoped is opt-in**, for "only in this project" / "just for this repo":

```bash
python3 "$TOGGLE" attach ~/brains/acme-business --scope project --cwd .
```

The target resolves to the **git root** when inside a repo, else the current
directory. **State the resolved path before linking** — the script prints it as
`target: ...`; put it in front of the member.

Scoping is additive, never shadowing: skills directories load together, so a
project attachment stacks on top of whatever is global.

### Already attached somewhere else

A project attach for a brain that is already global — or a global attach for
one already on in this project — exits **3** and does nothing. Do not retry
blindly. Offer the choice in their words:

> `hormozi` is already on everywhere. Do you want it on only inside this
> project instead, or left on everywhere?

Re-run with `--move` only if they choose to move. Never end up with the same
brain attached twice in one harness — that loads two copies of its front page.
The check is per harness: the same brain on in Claude Code *and* in Codex is
fine, since no single agent loads both — and that pair is a mechanics detail, so
it stays out of the member's answer unless they use both tools.

## Detaching

```bash
python3 "$TOGGLE" detach hormozi                      # global
python3 "$TOGGLE" detach acme-business --scope project --cwd .
```

Detach removes a symlink and nothing else; the brain folder is untouched. Say
that part out loud — *"switched off; the brain itself is still at
`~/brains/hormozi`, so turning it back on is one line"* — because "detached"
sounds like "deleted" to someone who has just built one. If something other than
a link sits at the target, the script refuses and says so — relay that rather
than deleting anything by hand. Confirm first when detaching more than one brain
at once.

## Listing

```bash
python3 "$TOGGLE" list --cwd .
```

Reports every scope it scanned and what is attached in each.
`(BROKEN: target is gone)` means the brain was moved or deleted out from under
the link. This lists what is *attached*, not what is installed — an inventory
of the brains on the machine is out of scope for v1.

**Answer it as a sentence, not a dump of the scan.** The member asked which
brains are on; give them that, plus where each one applies, and mention a second
tool only under the rules above. A brain folder that also happens to be a skill
directory is not worth explaining — say which of the things found are brains and
move on.

> `hormozi` is on everywhere. Nothing extra is switched on just for this
> project, and no brain is pointing at a folder that has gone missing.

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
python3 "$TOGGLE" pointer-diff ~/.gemini/GEMINI.md ~/brains/hormozi
python3 "$TOGGLE" pointer-add  ~/.gemini/GEMINI.md ~/brains/hormozi
python3 "$TOGGLE" pointer-remove ~/.gemini/GEMINI.md hormozi
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
  between its own delimiters, and removal restores the file byte for byte. The
  one exception, and it is unavoidable: a file that did not end in a newline
  gains one, because a line cannot be appended to a file that does not end.
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
linter first — to the member that is *"a check that every page carries the
details it needs and every link goes somewhere real"*, not "a lint pass":

```bash
python3 ~/.claude/skills/brain-builder/scripts/lint.py ~/brains/hormozi
```
