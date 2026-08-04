#!/usr/bin/env python3
"""Phase 4 (scaffold part) — create the portable brain skill folder.

Usage: build_brain.py <out_dir> "<topic>"

Creates ~/.claude/skills/brain-<slug>/ with the proven expert-brain layout:
SKILL.md (skeleton), references/{synthesis,quote-library,experts}.md (stubs for
Claude to fill), sources/ (cleaned transcripts copied in) + sources-index.md,
CHANGELOG.md, examples/. Claude then writes the actual knowledge into the stubs
by reading the transcripts. Prints the brain dir path + a fill-in checklist.
"""
import datetime
import json
import os
import re
import shutil
import sys


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:50] or "topic"


def main():
    out_dir = sys.argv[1]
    topic = sys.argv[2]
    today = datetime.date.today().isoformat()
    slug = slugify(topic)
    brain = os.path.expanduser(f"~/.claude/skills/brain-{slug}")
    os.makedirs(os.path.join(brain, "references"), exist_ok=True)
    os.makedirs(os.path.join(brain, "sources"), exist_ok=True)
    os.makedirs(os.path.join(brain, "examples"), exist_ok=True)

    sel = json.load(open(os.path.join(out_dir, "selected.json")))
    tindex_path = os.path.join(out_dir, "transcripts", "_index.json")
    tindex = json.load(open(tindex_path)) if os.path.exists(tindex_path) else {}

    # copy transcripts into the brain's sources/
    src_t = os.path.join(out_dir, "transcripts")
    copied = []
    if os.path.isdir(src_t):
        for fn in os.listdir(src_t):
            if fn.endswith(".txt"):
                shutil.copy(os.path.join(src_t, fn), os.path.join(brain, "sources", fn))
                copied.append(fn[:-4])

    # sources-index.md (the scored list, human-readable)
    lines = [f"# Sources — {topic}", "",
             f"Mined {today}. {sel['selected_count']} videos, "
             f"mix: {json.dumps(sel['mix'])}.", "",
             "| Score | Views | Engmt | Bucket | Gem | Channel | Title | Why |",
             "|------:|------:|------:|--------|-----|---------|-------|-----|"]
    for v in sel["selected"]:
        got = tindex.get(v["id"], {}).get("ok")
        mark = "" if got else " (no transcript)"
        lines.append("| {s} | {vw} | {er} | {bk} | {gem} | {ch} | {ti}{mk} | {why} |".format(
            s=v["score"], vw=v.get("view_count"), er=v.get("engagement_rate"),
            bk=v["bucket"], gem="Y" if v["is_hidden_gem"] else "",
            ch=(v.get("channel") or "")[:24],
            ti=(v.get("title") or "")[:48].replace("|", "/"), mk=mark,
            why="; ".join(v.get("reasons", []))[:60]))
    open(os.path.join(brain, "sources", "sources-index.md"), "w").write("\n".join(lines))

    # SKILL.md skeleton (Claude fills the KNOWLEDGE section)
    skill = f"""---
name: brain-{slug}
description: >
  Expert brain on {topic}. Collated from {sel['selected_count']} YouTube videos
  by both well-known experts and high-signal lesser-known voices (selected by
  engagement and substance, not view count). Use when speaking, writing,
  advising, or answering questions about {topic}; when you need the expert
  consensus, the contrarian takes, the named frameworks, or attributed quotes
  on {topic}.
metadata:
  type: expert-brain
  topic: "{topic}"
  built: "{today}"
  sources: {sel['selected_count']}
---

# Brain: {topic}

> Built by topic-brain-builder from {sel['selected_count']} YouTube sources
> ({sel['mix'].get('hidden_gems', 0)} hidden-gem creators surfaced on engagement,
> not views). Made by Selr AI.

## How to use this brain

When the user is working on {topic}, load this brain first. Ground answers in
the synthesis below and cite experts by name from the quote library. Prefer the
consensus view; surface a contrarian take when it's well-argued. The raw
transcripts are in `sources/` if you need to verify or quote precisely.

## What the experts agree on

<!-- FILL: 4-8 consensus points, each with which experts back it. -->

## Named frameworks & methods

<!-- FILL: the specific frameworks/methods/numbers experts named, attributed. -->

## Contrarian / disputed takes

<!-- FILL: where credible experts disagree, and who argues what. -->

## Deeper references

- `references/synthesis.md` — full thematic synthesis
- `references/quote-library.md` — verbatim quotes with attribution
- `references/experts.md` — who was mined and why (popular vs hidden-gem)
- `sources/` — cleaned transcripts + `sources-index.md` (the scored list)
"""
    open(os.path.join(brain, "SKILL.md"), "w").write(skill)

    # reference stubs
    open(os.path.join(brain, "references", "synthesis.md"), "w").write(
        f"# Synthesis — {topic}\n\n<!-- FILL by reading sources/*.txt: cluster into "
        "themes; under each theme give the point, the experts who back it, and a "
        "concrete number or example. Mark consensus vs contested. -->\n")
    open(os.path.join(brain, "references", "quote-library.md"), "w").write(
        f"# Quote Library — {topic}\n\n<!-- FILL: verbatim golden quotes. Format:\n"
        "> \"quote\" — Creator, *Video Title* -->\n")
    open(os.path.join(brain, "references", "experts.md"), "w").write(
        f"# Experts Mined — {topic}\n\n<!-- FILL: per creator — name, popular or "
        "hidden-gem, their angle/specialty, what they uniquely contribute. -->\n")

    open(os.path.join(brain, "CHANGELOG.md"), "w").write(
        f"# Changelog\n\n## {today}\n- Brain built from {sel['selected_count']} "
        f"YouTube sources via topic-brain-builder. Engine: {sel.get('engine')}. "
        f"Mix: {json.dumps(sel['mix'])}.\n")

    print(json.dumps({"brain_dir": brain, "transcripts_copied": len(copied),
                      "to_fill": ["SKILL.md knowledge sections",
                                  "references/synthesis.md",
                                  "references/quote-library.md",
                                  "references/experts.md"]}))


if __name__ == "__main__":
    main()
