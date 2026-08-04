---
name: brain-toggle
description: Turn a knowledge brain on or off for this machine's agent harnesses. Use when the user says "turn on my <name> brain", "attach the <name> brain", "switch off the <name> brain", "detach <name>", "which brains do I have", "list my brains", or otherwise wants to load, unload, or inspect installed brains.
---

# Brain Toggle

Attaches and detaches **brains** — standalone knowledge folders — to whichever agent harness is in use. A brain that is attached costs roughly its `SKILL.md` description in idle context; the body only loads when the router fires.

Brains live in `~/brains/<slug>/`. Each is a folder containing `SKILL.md`, `index.md`, `wiki/`, and optionally `persona/`.

## Operations

### List

Show every brain in `~/brains/`, and for each, whether it is currently attached in the Claude Code user skills directory.

```bash
for b in ~/brains/*/; do
  s=$(basename "$b")
  if [ -L ~/.claude/skills/"$s" ]; then echo "$s  [on]"; else echo "$s  [off]"; fi
done
```

### Attach

Symlink the brain folder into the harness's skills directory. This is the whole mechanism — no copying, no restart, persists across sessions.

| Harness | Target |
|---|---|
| Claude Code (user) | `~/.claude/skills/<slug>` |
| Claude Code (project) | `./.claude/skills/<slug>` |
| Claude Agent SDK | same dirs as Claude Code |
| Codex | `~/.codex/skills/<slug>` or `./.codex/skills/<slug>` |
| Any SKILL.md-standard harness | its skills dir |

```bash
mkdir -p ~/.claude/skills
ln -sfn ~/brains/<slug> ~/.claude/skills/<slug>
```

For harnesses that read an instruction file instead of a skills directory (OpenClaw's `AGENTS.md`, Hermes, Gemini), append a **pointer line** — never paste brain content, because workspace files inject whole on every turn:

```
The <slug> brain is available at ~/brains/<slug>/. Start at its index.md.
```

### Detach

```bash
rm ~/.claude/skills/<slug>
```

Remove the pointer line for instruction-file harnesses.

## Rules

- **Ask which harness** only if it is ambiguous. If the user is in Claude Code, default to the Claude Code user directory.
- **Never `rm -rf`** the target. Detach removes a symlink; if the path is not a symlink, stop and tell the user — something else put a real directory there.
- **Confirm before detaching** more than one brain at once.
- After attaching, tell the user the brain is on and that it will be picked up by the next thing that matches its description.
