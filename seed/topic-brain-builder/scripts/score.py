#!/usr/bin/env python3
"""Phase 2 — the "not just views" expertise scorer.

Usage: score.py <out_dir> [target_count]

Reads <out_dir>/candidates.json, computes a composite Expertise Score that
DE-WEIGHTS raw view count, deliberately boosts high-engagement hidden gems,
keeps a spread of new + evergreen videos, and caps videos-per-channel so no
single creator dominates. Writes <out_dir>/selected.json (the cut list, with a
plain-English reason each video made it) plus the full ranked table.
"""
import datetime
import json
import math
import os
import statistics
import sys

CFG = {
    "target": 28,            # ~25-30 videos
    "max_per_channel": 3,
    "min_duration": 180,     # skip <3min unless engagement exceptional
    "hidden_gem_view_ceiling": 20000,   # "low view" threshold for the gem boost
    "new_cutoff_days": 365,  # <1yr = "new", else "evergreen"
}


def _days_old(yyyymmdd):
    try:
        d = datetime.datetime.strptime(yyyymmdd, "%Y%m%d").date()
        return (datetime.date.today() - d).days
    except Exception:
        return None


def _engagement_rate(v):
    views = max(v.get("view_count") or 0, 1)
    likes = v.get("like_count") or 0
    comments = v.get("comment_count") or 0
    # comments weigh 3x a like — a comment is a higher-effort signal of value
    return (likes + comments * 3) / views


def score_all(cands):
    # engagement percentiles (for hidden-gem detection)
    rates = [_engagement_rate(c) for c in cands] or [0]
    try:
        p80 = statistics.quantiles(rates, n=10)[7] if len(rates) >= 10 else max(rates)
    except Exception:
        p80 = max(rates)

    scored = []
    for c in cands:
        views = c.get("view_count") or 0
        er = _engagement_rate(c)
        days = _days_old(c.get("upload_date") or "")
        dur = c.get("duration") or 0
        reasons = []

        # 1. Engagement rate is the PRIMARY signal (0..~40), log-scaled
        er_score = min(40.0, er * 4000.0)

        # 2. View score is intentionally SMALL + log-scaled (so a 2M-view video
        #    only modestly outranks a 5k-view one on reach alone)
        view_score = min(12.0, math.log10(max(views, 1)) * 2.0)

        # 3. Hidden-gem boost: low views + top-decile engagement
        gem = False
        gem_boost = 0.0
        if views and views <= CFG["hidden_gem_view_ceiling"] and er >= p80:
            gem_boost = 15.0
            gem = True
            reasons.append("hidden gem (small channel, top-decile engagement)")

        # 4. Substance: duration floor (real teaching, not a 40s short)
        dur_score = 0.0
        if dur >= CFG["min_duration"]:
            dur_score = min(8.0, dur / 600.0 * 8.0)  # rewards up to ~10min
        elif er < p80:
            er_score *= 0.4  # penalise low-engagement shorts hard
            reasons.append("short + low engagement (penalised)")

        # 5. Authority sanity (subs help a little, capped — not the driver)
        subs = c.get("channel_subs") or 0
        sub_score = min(6.0, math.log10(max(subs, 1)) * 1.2)

        total = er_score + view_score + gem_boost + dur_score + sub_score
        bucket = "evergreen"
        if days is not None and days <= CFG["new_cutoff_days"]:
            bucket = "new"

        if not reasons:
            if views and views > 200000:
                reasons.append("popular expert (high reach + solid engagement)")
            else:
                reasons.append("strong engagement for its size")

        scored.append({**c, "engagement_rate": round(er, 5), "bucket": bucket,
                       "days_old": days, "is_hidden_gem": gem,
                       "score": round(total, 2), "reasons": reasons})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def select(scored, target):
    per_channel = {}
    chosen, new_n, ever_n = [], 0, 0
    for v in scored:
        if len(chosen) >= target:
            break
        ch = v.get("channel_id") or v.get("channel") or "?"
        if per_channel.get(ch, 0) >= CFG["max_per_channel"]:
            continue
        per_channel[ch] = per_channel.get(ch, 0) + 1
        chosen.append(v)
        if v["bucket"] == "new":
            new_n += 1
        else:
            ever_n += 1
    return chosen, {"new": new_n, "evergreen": ever_n,
                    "hidden_gems": sum(1 for v in chosen if v["is_hidden_gem"]),
                    "channels": len(per_channel)}


def main():
    out_dir = sys.argv[1]
    target = int(sys.argv[2]) if len(sys.argv) > 2 else CFG["target"]
    data = json.load(open(os.path.join(out_dir, "candidates.json")))
    scored = score_all(data["candidates"])
    chosen, mix = select(scored, target)
    result = {"topic": data["topic"], "engine": data.get("engine"),
              "selected_count": len(chosen), "mix": mix,
              "selected": chosen, "ranked_all": scored}
    with open(os.path.join(out_dir, "selected.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({"selected": len(chosen), "mix": mix}))


if __name__ == "__main__":
    main()
