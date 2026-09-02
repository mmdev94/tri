#!/usr/bin/env bash
# Recommended weekly vision: sync → bare → factors → (optional) promote → template check.
# Does NOT run full OpenClaw eval (use eval-one.sh / run-vps-eval.sh after allows).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/miner-lab"
LABEL="${1:-lab}"

cd "$ROOT"
set -a
[[ -f .env ]] && . ./.env
[[ -f tri-check/.env ]] && . ./tri-check/.env
set +a

echo "=== sync ==="
python3 "$LAB/sync-challenge.py"

echo "=== bare ==="
python3 "$LAB/baseline-input.py" --mode bare --label "${LABEL}-bare" || true

echo "=== factors ==="
python3 "$LAB/baseline-input.py" --mode factors --label "${LABEL}-factors" || true

echo "=== current template vs bare (Q3,Q4,Q6 soft-ish) ==="
python3 "$LAB/baseline-input.py" --mode bare,template --qid Q3 --label "${LABEL}-q3" || true
python3 "$LAB/baseline-input.py" --mode bare,template --qid Q4 --label "${LABEL}-q4" || true
python3 "$LAB/baseline-input.py" --mode bare,template --qid Q6 --label "${LABEL}-q6" || true

echo "=== done ==="
echo "Read: $LAB/lab/LATEST-BASELINE.md"
echo "Promote a winner:  python3 $LAB/promote-factor.py archive_short --snapshot"
echo "One-Q eval:        bash $LAB/eval-one.sh Q6 --label try1"
echo "Full eval:         bash $LAB/run-vps-eval.sh --label after-allow"
