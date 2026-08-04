# Example session — building a brain on "cold email deliverability"

A real run of the 6-phase pipeline (balanced depth, trimmed to 8 for the demo).

**User:** build me a brain on cold email deliverability

**Phase 0 — engine**
```
$ python3 scripts/engine.py detect
{"engine": "yt-dlp", "note": "Using yt-dlp (no key needed)."}
```
> Using yt-dlp — no key needed.

**Phase 1 — discover**
```
$ python3 scripts/discover.py "cold email deliverability" "$OUT" 3
{"engine": "yt-dlp", "candidates": 13}
```

**Phase 2 — score** (the not-just-views engine)
```
$ python3 scripts/score.py "$OUT" 8
{"selected": 8, "mix": {"new": 5, "evergreen": 3, "hidden_gems": 2, "channels": 8}}
```
Top of the cut list — note the two hidden gems outranking the popular video:

| score | views | engagement | gem | channel | title |
|------:|------:|-----------:|-----|---------|-------|
| 73.1 | 673 | 0.095 | Y | Hoani Taylor | Ultimate Cold Email Deliverability Guide |
| 70.3 | 95 | 0.158 | Y | Atishay Jain | Cold Email Deliverability In 2026 |
| 62.1 | 13,171 | 0.036 | | Instantly | The Ultimate Guide to Cold Email Deliverability |
| 61.8 | 17,106 | 0.043 | | Max Sturtevant | 2024 Email Deliverability Guide |

A 95-view video from a niche operator beat a 13k-view channel because its
engagement rate was 4x higher. That is the whole point: depth over reach.

**Phase 3 — transcripts**
```
$ python3 scripts/extract.py "$OUT"
{"transcripts_ok": 8, "attempted": 8}
```

**Phase 4 — scaffold**
```
$ python3 scripts/build_brain.py "$OUT" "cold email deliverability"
{"brain_dir": ".../brain-cold-email-deliverability", "transcripts_copied": 8}
```

**Phase 4b — fill (model reads the 8 transcripts, ~31k words)** and writes the
synthesis, quote library and experts map. **Phase 5** reports:

> Built brain-cold-email-deliverability from 8 sources (2 hidden-gem creators
> surfaced on engagement, not views), 8 transcripts, 14 attributed quotes.
> Lives at ~/.claude/skills/brain-cold-email-deliverability/. Ask about cold
> email deliverability in any new chat and it loads.
