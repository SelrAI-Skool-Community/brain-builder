# Changelog

## 1.0.0 — 2026-05-28

Initial release. One-touch topic → expert brain builder.

- 6-phase pipeline: engine auto-detect → multi-angle discover → expertise score
  → transcript extract → scaffold brain → fill + sync to gbrain.
- **Engine ladder**: yt-dlp (universal default, self-installing, no key) →
  YouTube Data API v3 (user's own key, optional) → Apify (optional, if token).
  gws confirmed unable to reach YouTube and excluded.
- **Not-just-views scorer** (`scripts/score.py`): leads on engagement rate +
  substance, boosts low-view/high-engagement hidden gems, caps videos per
  channel, keeps a new/evergreen mix.
- Outputs a portable `brain-<topic>` skill (SKILL.md + synthesis + quote library
  + experts map + transcripts) and syncs into the shared gbrain when reachable.
- Verified end-to-end on "cold email deliverability": 13 candidates → 8 selected
  with two sub-1k-view hidden gems ranked above a 13k-view popular video → 8/8
  transcripts pulled → brain scaffolded.
