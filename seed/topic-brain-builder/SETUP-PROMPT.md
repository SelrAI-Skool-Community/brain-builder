# SETUP-PROMPT.md

Paste this into Claude Code to install + verify `topic-brain-builder`.

```
Install and verify the topic-brain-builder skill for me, end to end. No questions.

1. Confirm the skill is at ~/.claude/skills/topic-brain-builder/ (SKILL.md + scripts/).
2. Make sure an engine is available: run `python3 ~/.claude/skills/topic-brain-builder/scripts/engine.py detect`. It auto-installs yt-dlp if needed and returns the chosen engine as JSON. If it still reports none, you (Claude) resolve it and re-run — never hand this to the user.
3. Read SKILL.md so you know the 6-phase flow and trigger phrases.
4. Tell me it's ready and give me one example command, like: build a brain on "cold email deliverability".

If anything fails, fix it yourself and retry. Don't stop to ask.
```

## What this skill does

Name a topic, and it finds the best YouTube experts on it — popular names AND
high-signal lesser-known voices, ranked by engagement and substance rather than
raw views — pulls the transcripts, collates the best information, and writes a
reusable `brain-<topic>` skill you can load whenever you speak or write about
that subject. Full operation map is in `SKILL.md`.

## Requirements

- **yt-dlp** (the skill installs it if missing). No API key needed.
- Optional: your own free YouTube Data API key in `YT_API_KEY` for the official
  API path; an `APIFY_TOKEN` for richer comment mining. Neither is required.

## Self-heal

If a step fails (missing tool, a video without captions, a thin result pool),
the skill retries / installs / broadens / skips and keeps going. It does not
hand work back to you.

Made by Selr AI.
