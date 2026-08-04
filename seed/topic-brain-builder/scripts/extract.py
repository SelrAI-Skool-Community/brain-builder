#!/usr/bin/env python3
"""Phase 3 (mechanical part) — download + clean transcripts for selected videos.

Usage: extract.py <out_dir>

Reads <out_dir>/selected.json, downloads English captions for each selected
video via yt-dlp (auto-subs ok), strips VTT timing/markup to clean prose, and
writes <out_dir>/transcripts/<id>.txt. Writes transcripts/_index.json mapping
id -> {title, channel, ok}. Claude then READS these to extract claims, quotes
and synthesis (that part is not scripted — it's the model's job).
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile


def clean_vtt(path):
    raw_lines = []
    for raw in open(path, encoding="utf-8", errors="ignore"):
        s = raw.strip()
        if not s or s == "WEBVTT" or "-->" in s:
            continue
        if s.startswith(("Kind:", "Language:", "NOTE")):
            continue
        s = re.sub(r"<[^>]+>", "", s)            # inline timing tags
        s = re.sub(r"\[[^\]]*\]", "", s)          # [Music] etc
        s = s.strip()
        if s:
            raw_lines.append(s)
    # Collapse YouTube auto-sub rolling duplicates: each caption grows word by
    # word, so a line that is just a prefix of the next is an in-progress copy.
    lines = []
    for i, s in enumerate(raw_lines):
        nxt = raw_lines[i + 1] if i + 1 < len(raw_lines) else ""
        if nxt.startswith(s):
            continue
        if lines and lines[-1] == s:
            continue
        lines.append(s)
    text = " ".join(lines)
    return re.sub(r"\s+", " ", text).strip()


def fetch(video_id, dest_txt):
    with tempfile.TemporaryDirectory() as td:
        # YouTube now requires login cookies (bot check) plus a JS runtime with
        # the EJS challenge solver to expose caption formats. Layer those on,
        # then fall back to lighter recipes if a video doesn't need them.
        base = ["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
                "--sub-langs", "en.*", "--sub-format", "vtt",
                "--ignore-no-formats-error", "--sleep-requests", "1",
                "-o", os.path.join(td, "%(id)s.%(ext)s"), "--no-warnings",
                f"https://www.youtube.com/watch?v={video_id}"]
        cookie_browser = os.environ.get("YT_COOKIES_FROM_BROWSER", "chrome")
        attempts = [
            ["--cookies-from-browser", cookie_browser, "--js-runtimes", "node",
             "--remote-components", "ejs:github"],
            ["--cookies-from-browser", cookie_browser],
            [],  # anonymous last resort
        ]
        vtts = []
        for extra in attempts:
            try:
                subprocess.run(base + extra, capture_output=True, timeout=240)
            except Exception:
                continue
            vtts = glob.glob(os.path.join(td, "*.vtt"))
            if vtts:
                break
        if not vtts:
            return False
        text = clean_vtt(sorted(vtts)[0])
        if len(text) < 200:
            return False
        with open(dest_txt, "w") as f:
            f.write(text)
        return True


def main():
    out_dir = sys.argv[1]
    tdir = os.path.join(out_dir, "transcripts")
    os.makedirs(tdir, exist_ok=True)
    sel = json.load(open(os.path.join(out_dir, "selected.json")))
    index = {}
    ok = 0
    for v in sel["selected"]:
        vid = v["id"]
        dest = os.path.join(tdir, f"{vid}.txt")
        got = fetch(vid, dest)
        index[vid] = {"title": v.get("title"), "channel": v.get("channel"),
                      "is_hidden_gem": v.get("is_hidden_gem"), "ok": got}
        if got:
            ok += 1
    json.dump(index, open(os.path.join(tdir, "_index.json"), "w"), indent=2)
    print(json.dumps({"transcripts_ok": ok, "attempted": len(sel["selected"])}))


if __name__ == "__main__":
    main()
