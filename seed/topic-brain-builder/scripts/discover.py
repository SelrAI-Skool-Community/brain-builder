#!/usr/bin/env python3
"""Phase 1 — multi-angle discovery.

Usage: discover.py "<topic>" <out_dir> [per_angle]

Expands the topic into several search angles so breadth isn't missed, runs each
through the engine, dedupes, then pulls full metadata for every unique candidate.
Writes <out_dir>/candidates.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402

ANGLES = [
    "{t}",
    "{t} tutorial",
    "how to {t}",
    "{t} mistakes",
    "{t} framework",
    "{t} explained",
    "advanced {t}",
    "{t} strategy",
]


def main():
    topic = sys.argv[1]
    out_dir = sys.argv[2]
    per_angle = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    os.makedirs(out_dir, exist_ok=True)

    det = engine.detect()
    eng = det["engine"]
    if not eng:
        print(json.dumps({"error": det["note"]}))
        sys.exit(1)

    seen, candidates = set(), []
    for tpl in ANGLES:
        q = tpl.format(t=topic)
        for row in engine.search(q, per_angle, engine=eng):
            vid = row["id"]
            if vid in seen:
                continue
            seen.add(vid)
            row["found_via"] = q
            candidates.append(row)

    ids = [c["id"] for c in candidates]
    meta = {m["id"]: m for m in engine.metadata(ids, engine=eng)}
    enriched = []
    for c in candidates:
        m = meta.get(c["id"])
        if not m:
            continue
        m["found_via"] = c.get("found_via")
        enriched.append(m)

    result = {"topic": topic, "engine": eng, "engine_note": det["note"],
              "angles": [t.format(t=topic) for t in ANGLES],
              "candidate_count": len(enriched), "candidates": enriched}
    with open(os.path.join(out_dir, "candidates.json"), "w") as f:
        json.dump(result, f, indent=2)

    # Guard: too few candidates means the topic is too narrow/odd to build a real
    # brain. Tell the user plainly and stop — don't build an empty brain.
    if len(enriched) < 4:
        print(json.dumps({
            "engine": eng, "candidates": len(enriched), "too_thin": True,
            "advice": "Too few videos found for this exact phrasing. Try a broader "
                      "or more common topic (e.g. 'cold email' not 'cold email for "
                      "left-handed plumbers'), or rerun with a higher per-angle count."}))
        sys.exit(2)
    print(json.dumps({"engine": eng, "note": det["note"],
                      "candidates": len(enriched)}))


if __name__ == "__main__":
    main()
