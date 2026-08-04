# Scoring rubric — why a video makes the cut (and why views barely matter)

The scorer in `scripts/score.py` ranks candidates by a composite **Expertise
Score**. The design goal: surface genuine expertise, including from small
creators, and never let raw view count dominate.

## Components

| Component | Max | What it rewards |
|-----------|----:|-----------------|
| Engagement rate | ~40 | `(likes + 3×comments) / views`, log-scaled. The primary signal. A comment counts 3× a like (higher-effort signal of value). |
| Hidden-gem boost | +15 | Views ≤ 20k AND engagement in the top decile of the candidate pool. This is what lifts lesser-known experts above popular fluff. |
| Substance (duration) | ~8 | Real teaching length. Sub-3-minute videos are penalised unless engagement is exceptional. |
| View score | ~12 | log-scaled and deliberately small — reach is a tie-breaker, not the driver. A 2M-view video only modestly outscores a 5k-view one on reach. |
| Channel authority | ~6 | log(subscribers), capped. A light sanity signal, not a gate. |

## Selection rules (after scoring)

- **Max 3 videos per channel** — no single creator dominates the brain.
- **New / evergreen mix** — videos <12 months old are "new", older are
  "evergreen"; the cut keeps both so the brain has current tactics + durable
  fundamentals.
- **Target ~25-30 videos / ~12-15 channels** at balanced depth.

## Why not just use YouTube's own ranking?

YouTube search and "most popular" both bias hard toward view count and recency,
which buries small experts. Two creators can both be right, but the one with
200k subscribers ranks first every time regardless of who taught it better. By
leading on engagement rate and explicitly boosting high-engagement low-view
videos, the brain captures the knowledgeable-but-less-popular voices the user
specifically asked for.

## Tuning

Edit the `CFG` dict at the top of `scripts/score.py`:
`target`, `max_per_channel`, `min_duration`, `hidden_gem_view_ceiling`,
`new_cutoff_days`.
