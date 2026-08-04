#!/usr/bin/env bash
# Smoke test for topic-brain-builder. Read-only, no network calls required to
# pass the structural checks. Exits non-zero on any failure.
set -u
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

ok()   { echo "  ok   $1"; }
bad()  { echo "  FAIL $1"; fail=1; }

echo "topic-brain-builder smoke"

# 1. SKILL.md frontmatter
grep -q "^name: topic-brain-builder" "$SKILL_DIR/SKILL.md" && ok "SKILL.md name" || bad "SKILL.md name"
grep -q "^description:" "$SKILL_DIR/SKILL.md" && ok "SKILL.md description" || bad "SKILL.md description"

# 2. pipeline scripts present + valid python
for s in engine.py discover.py score.py extract.py build_brain.py; do
  if [ -f "$SKILL_DIR/scripts/$s" ] && python3 -c "import ast;ast.parse(open('$SKILL_DIR/scripts/$s').read())" 2>/dev/null; then
    ok "scripts/$s parses"
  else
    bad "scripts/$s missing or invalid"
  fi
done

# 3. evidence files
for f in CHANGELOG.md SETUP-PROMPT.md examples/topic-brain-builder-session.md references/scoring-rubric.md; do
  [ -f "$SKILL_DIR/$f" ] && ok "$f" || bad "$f missing"
done

# 4. engine detect runs (does not require an engine to be present — just that it returns valid JSON)
if python3 "$SKILL_DIR/scripts/engine.py" detect 2>/dev/null | python3 -c "import json,sys;json.load(sys.stdin)" 2>/dev/null; then
  ok "engine.py detect returns JSON"
else
  bad "engine.py detect did not return JSON"
fi

# 5. scorer is deterministic on a fixture (hidden gem must outrank a high-view low-engagement video)
python3 - "$SKILL_DIR" <<'PY' && ok "scorer ranks hidden gem above high-view low-engagement" || bad "scorer ranking wrong"
import json, os, sys, tempfile
sd = sys.argv[1]
sys.path.insert(0, os.path.join(sd, "scripts"))
import score
cands = [
  {"id":"gem","title":"deep dive","channel":"Small","channel_id":"c1","channel_subs":800,
   "view_count":300,"like_count":45,"comment_count":20,"upload_date":"20260101","duration":900,"description":""},
  {"id":"pop","title":"viral","channel":"Big","channel_id":"c2","channel_subs":900000,
   "view_count":2000000,"like_count":8000,"comment_count":300,"upload_date":"20260101","duration":600,"description":""},
]
ranked = score.score_all(cands)
sys.exit(0 if ranked[0]["id"] == "gem" else 1)
PY

echo ""
if [ "$fail" -eq 0 ]; then echo "SMOKE PASS"; else echo "SMOKE FAIL"; fi
exit $fail
