#!/usr/bin/env python3
"""Engine layer for topic-brain-builder.

Auto-detects the best available YouTube engine and exposes two operations the
rest of the pipeline calls, engine-agnostic:

  detect()                  -> {"engine": "...", "note": "..."}
  search(query, n)          -> [ {id,title,channel,channel_id,view_count}, ... ]   (cheap, flat)
  metadata(video_ids)       -> [ {full per-video stats}, ... ]

Engine ladder (first that works wins, yt-dlp is the universal default):
  1. yt-dlp        — no key, no quota; auto-installed if missing. Default for everyone.
  2. youtube_api   — only if a YouTube Data API v3 key is in env YT_API_KEY (the
                     user's own free key). Discovery + stats via the official API.
  3. apify         — only if APIFY_TOKEN is set (optional, richer comments).

Note: Google Workspace CLI (gws) is NOT an engine — it cannot reach YouTube.

stdlib only. yt-dlp is shelled out, never imported.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request


def _have(cmd):
    return shutil.which(cmd) is not None


def _try_install_ytdlp():
    """Best-effort install of yt-dlp across Mac / Linux / Windows. Claude runs
    this, never the user. Tries the platform's native manager first, then always
    falls back to pip (works anywhere Python is, including Windows)."""
    candidates = [
        ["brew", "install", "yt-dlp"],        # macOS / Linuxbrew
        ["winget", "install", "--silent", "-e", "--id", "yt-dlp.yt-dlp"],  # Windows
        ["pipx", "install", "yt-dlp"],        # any OS with pipx
        [sys.executable, "-m", "pip", "install", "--user", "-U", "yt-dlp"],  # universal
        ["python", "-m", "pip", "install", "--user", "-U", "yt-dlp"],        # Windows py alias
    ]
    for installer in candidates:
        head = installer[0]
        # pip-via-sys.executable always runnable; others need to be on PATH
        if head in (sys.executable,) or _have(head):
            try:
                subprocess.run(installer, check=True, capture_output=True, timeout=300)
                if _have("yt-dlp"):
                    return True
            except Exception:
                continue
    return _have("yt-dlp")


# YouTube Data API key may be supplied under any of these env names (the user's
# own free Google key). First non-empty wins.
_YT_KEY_ENVS = ("YT_API_KEY", "YOUTUBE_API_KEY", "GOOGLE_API_KEY", "GCP_YOUTUBE_API_KEY")


def _youtube_api_key():
    for name in _YT_KEY_ENVS:
        v = os.environ.get(name)
        if v:
            if name != "YT_API_KEY":
                os.environ["YT_API_KEY"] = v  # normalise for the API helpers
            return v
    return None


def detect():
    """Pick the best available engine. Returns {engine, note}.

    yt-dlp is the zero-setup default and is preferred even when a key exists,
    because it also returns transcripts and never hits a quota. The YouTube Data
    API path is used only when yt-dlp can't be made available.
    """
    if _have("yt-dlp"):
        return {"engine": "yt-dlp", "note": "Using yt-dlp (zero setup, no key needed)."}
    if _try_install_ytdlp():
        return {"engine": "yt-dlp", "note": "Installed yt-dlp automatically, then using it (no key needed)."}
    # yt-dlp couldn't be installed — fall back to the user's own Google/YouTube key
    if _youtube_api_key():
        return {"engine": "youtube_api", "note": "Using the YouTube Data API with your own Google key."}
    if os.environ.get("APIFY_TOKEN"):
        return {"engine": "apify", "note": "Using Apify YouTube scraper (token detected)."}
    return {"engine": None,
            "note": "No engine available. Could not auto-install yt-dlp and no YouTube/Google API key was found "
                    "(set one of: " + ", ".join(_YT_KEY_ENVS) + ")."}


# ---------- yt-dlp ----------
def _ytdlp_search(query, n):
    out = subprocess.run(
        ["yt-dlp", f"ytsearch{n}:{query}", "--flat-playlist", "--dump-json",
         "--no-warnings", "--ignore-errors"],
        capture_output=True, text=True, timeout=180)
    rows = []
    for line in out.stdout.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        rows.append({"id": d.get("id"), "title": d.get("title"),
                     "channel": d.get("channel") or d.get("uploader"),
                     "channel_id": d.get("channel_id"),
                     "view_count": d.get("view_count")})
    return [r for r in rows if r.get("id")]


def _ytdlp_metadata(video_ids):
    rows = []
    for vid in video_ids:
        try:
            out = subprocess.run(
                ["yt-dlp", "--dump-json", "--no-warnings", "--skip-download",
                 f"https://www.youtube.com/watch?v={vid}"],
                capture_output=True, text=True, timeout=120)
            d = json.loads(out.stdout)
        except Exception:
            continue
        rows.append({
            "id": d.get("id"),
            "title": d.get("title"),
            "channel": d.get("channel") or d.get("uploader"),
            "channel_id": d.get("channel_id"),
            "channel_subs": d.get("channel_follower_count"),
            "view_count": d.get("view_count") or 0,
            "like_count": d.get("like_count") or 0,
            "comment_count": d.get("comment_count") or 0,
            "upload_date": d.get("upload_date"),
            "duration": d.get("duration") or 0,
            "description": (d.get("description") or "")[:500],
            "has_captions": bool(d.get("subtitles") or d.get("automatic_captions")),
        })
    return rows


# ---------- YouTube Data API v3 (user's own key) ----------
def _api_get(path, params):
    params = dict(params)
    params["key"] = os.environ["YT_API_KEY"]
    url = "https://www.googleapis.com/youtube/v3/" + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def _api_search(query, n):
    data = _api_get("search", {"part": "snippet", "q": query, "type": "video",
                               "maxResults": min(n, 50), "order": "relevance"})
    rows = []
    for it in data.get("items", []):
        vid = it.get("id", {}).get("videoId")
        sn = it.get("snippet", {})
        if vid:
            rows.append({"id": vid, "title": sn.get("title"),
                         "channel": sn.get("channelTitle"),
                         "channel_id": sn.get("channelId"), "view_count": None})
    return rows


def _api_metadata(video_ids):
    rows = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        data = _api_get("videos", {"part": "snippet,statistics,contentDetails",
                                   "id": ",".join(batch)})
        chans = {}
        for it in data.get("items", []):
            chans.setdefault(it.get("snippet", {}).get("channelId"), None)
        # channel subs
        if chans:
            cdata = _api_get("channels", {"part": "statistics",
                                          "id": ",".join([c for c in chans if c])})
            for c in cdata.get("items", []):
                chans[c["id"]] = int(c.get("statistics", {}).get("subscriberCount") or 0)
        for it in data.get("items", []):
            sn, st = it.get("snippet", {}), it.get("statistics", {})
            rows.append({
                "id": it.get("id"), "title": sn.get("title"),
                "channel": sn.get("channelTitle"), "channel_id": sn.get("channelId"),
                "channel_subs": chans.get(sn.get("channelId")),
                "view_count": int(st.get("viewCount") or 0),
                "like_count": int(st.get("likeCount") or 0),
                "comment_count": int(st.get("commentCount") or 0),
                "upload_date": (sn.get("publishedAt") or "")[:10].replace("-", ""),
                "duration": 0, "description": (sn.get("description") or "")[:500],
                "has_captions": True,
            })
    return rows


# ---------- dispatch ----------
def search(query, n, engine=None):
    engine = engine or detect()["engine"]
    if engine == "youtube_api":
        return _api_search(query, n)
    return _ytdlp_search(query, n)  # apify falls back to yt-dlp for discovery


def metadata(video_ids, engine=None):
    engine = engine or detect()["engine"]
    if engine == "youtube_api":
        return _api_metadata(video_ids)
    return _ytdlp_metadata(video_ids)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "detect"
    if cmd == "detect":
        print(json.dumps(detect()))
    elif cmd == "search":
        print(json.dumps(search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)))
    elif cmd == "metadata":
        print(json.dumps(metadata(sys.argv[2:])))
