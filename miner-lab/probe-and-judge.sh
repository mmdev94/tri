#!/usr/bin/env bash
# Gate → judge bridge: Halo-probe soft Qs with current submission, then eval-one each allow.
#
# Usage:
#   bash miner-lab/probe-and-judge.sh
#   bash miner-lab/probe-and-judge.sh --qids Q3,Q6 --label gate1
#   bash miner-lab/probe-and-judge.sh --submission miner-lab/submission.json

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/miner-lab"
QIDS="Q3,Q4,Q6"
LABEL="gate"
SUBMISSION="$LAB/submission.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --qids) QIDS="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --submission) SUBMISSION="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown: $1" >&2; exit 2 ;;
  esac
done

cd "$ROOT"
set -a
[[ -f .env ]] && . ./.env
[[ -f tri-check/.env ]] && . ./tri-check/.env
set +a

echo "=== Halo template probe ($QIDS) ==="
python3 "$LAB/baseline-input.py" --mode template --submission "$SUBMISSION" \
  --qids "$QIDS" --label "${LABEL}-probe"

# Parse latest baseline JSON for allows on template variant
ALLOWS="$(python3 - <<'PY'
import json
from pathlib import Path
lab = Path("miner-lab/lab")
cands = sorted(lab.glob("baseline-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
if not cands:
    raise SystemExit("no baseline json")
data = json.loads(cands[0].read_text())
allows = []
for r in data.get("results") or []:
    if r.get("variant") == "template" and r.get("verdict") == "allow":
        allows.append(r.get("question_id"))
print(",".join(allows))
print(cands[0].name, file=__import__("sys").stderr)
PY
)"

if [[ -z "$ALLOWS" ]]; then
  echo "No input allows on soft Qs — skip judge. Archive wraps often allow but score 0; do not submit on allow alone."
  exit 0
fi

echo "=== Input allows: $ALLOWS — running eval-one each ==="
IFS=',' read -ra QS <<< "$ALLOWS"
HIST="$LAB/lab/JUDGE-HISTORY.md"
mkdir -p "$LAB/lab"
if [[ ! -f "$HIST" ]]; then
  cat >"$HIST" <<'EOF'
# Judge history (after input allow)

| UTC | Label | Q | Judge | Block | Note |
|-----|-------|---|-------|-------|------|
EOF
fi

UTC="$(date -u +%Y-%m-%dT%H:%MZ)"
TOTAL=0
for q in "${QS[@]}"; do
  [[ -z "$q" ]] && continue
  echo "--- eval-one $q ---"
  set +e
  bash "$LAB/eval-one.sh" "$q" --label "${LABEL}-${q}" --submission "$SUBMISSION"
  RC=$?
  set -e
  # scrape score from shared latest or run summary
  SCORE="$(python3 - <<PY
import json
from pathlib import Path
rep = Path("results/miner-lab/LATEST/report.json")
if not rep.is_file():
    print(0)
    raise SystemExit
d = json.loads(rep.read_text())
want = "$q"
for r in d.get("results") or []:
    qid = r.get("questionId") or r.get("question_id") or r.get("id")
    if qid == want or len(d.get("results") or []) == 1:
        s = r.get("judgeScore")
        print(int(s) if s is not None else 0)
        break
else:
    print(0)
PY
)"
  BLOCK="$(python3 - <<PY
import json
from pathlib import Path
rep = Path("results/miner-lab/LATEST/report.json")
if not rep.is_file():
    print("?")
    raise SystemExit
d = json.loads(rep.read_text())
r = (d.get("results") or [{}])[0]
text = (r.get("modelResponse") or r.get("response") or r.get("openclawResponse") or "")
t = str(text).lower()
if "blocked by input" in t:
    print("input")
elif "blocked by output" in t:
    print("output")
else:
    print("ok")
PY
)"
  TOTAL=$((TOTAL + SCORE))
  echo "| $UTC | $LABEL | $q | $SCORE | $BLOCK | probe-and-judge rc=$RC |" >>"$HIST"
  echo "Q=$q judge=$SCORE block=$BLOCK"
done

echo "=== done soft-Q judge sum=$TOTAL (max $(( ${#QS[@]} * 2 ))) ==="
echo "History: $HIST"
echo "Note: archival CASE_NOTE responses usually score 0 — gate track ≠ score track."
exit 0
