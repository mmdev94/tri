#!/usr/bin/env bash
# Weekly lab pass — respects freeze (no archive evolve by default).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/miner-lab"
LABEL="${1:-lab}"

cd "$ROOT"
set -a
[[ -f .env ]] && . ./.env
[[ -f tri-check/.env ]] && . ./tri-check/.env
set +a

echo "=== status ==="
cat "$LAB/lab/STATUS.md" || true

echo "=== sync ==="
python3 "$LAB/sync-challenge.py"

echo "=== score-track factors (factors.json) ==="
set +e
python3 "$LAB/baseline-input.py" --mode factors --qids Q3,Q4,Q6 --label "${LABEL}-score"
RC=$?
set -e
if [[ "$RC" -eq 3 ]]; then
  echo "Score factors empty (expected after freeze). Add new families to factors.json."
fi

echo "=== done ==="
echo "Gate regression (optional): python3 $LAB/baseline-input.py --mode factors --factors-file $LAB/factors.gate.json --qids Q3,Q4,Q6"
echo "Judge bridge:              bash $LAB/probe-and-judge.sh --label ${LABEL}"
echo "Upload only if JUDGE-HISTORY soft sum > 0"
