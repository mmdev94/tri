#!/usr/bin/env bash
# Batch search: Stage A (Halo input on all factors) → Stage B (judge on survivors).
#
# Usage (repo root, OpenClaw up for Stage B):
#   bash miner-lab/batch-search.sh --label b7
#   bash miner-lab/batch-search.sh --stage a --label b7
#   bash miner-lab/batch-search.sh --stage b --label b7
#   python3 miner-lab/evolve-factors.py --mode explore --merge --label evo7
#   bash miner-lab/batch-search.sh --label evo7
#
# Stage B skips CASE_NOTE family by default (known judge 0).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/miner-lab"
STAGE="all"
QIDS="Q3,Q4,Q6"
JUDGE_QIDS="Q3,Q6"
MAX_JUDGE=8
LABEL="batch"
INCLUDE_CASE_NOTE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stage) STAGE="$2"; shift 2 ;;
    --qids) QIDS="$2"; shift 2 ;;
    --judge-qids) JUDGE_QIDS="$2"; shift 2 ;;
    --max-judge) MAX_JUDGE="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --include-case-note) INCLUDE_CASE_NOTE=1; shift ;;
    -h|--help)
      sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
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

SURVIVORS="$LAB/lab/BATCH-SURVIVORS.json"
BATCH_MD="$LAB/lab/LATEST-BATCH.md"
mkdir -p "$LAB/lab"

run_stage_a() {
  echo "========== STAGE A: Halo input ($QIDS) =========="
  n="$(python3 -c "import json; d=json.load(open('miner-lab/factors.json')); print(sum(1 for k,v in d.items() if not k.startswith('_') and isinstance(v,str)))")"
  if [[ "$n" -eq 0 ]]; then
    echo "ERROR: factors.json has 0 templates — add seeds or evolve --merge first." >&2
    exit 3
  fi
  echo "factors=$n"
  set +e
  python3 "$LAB/baseline-input.py" --mode factors --qids "$QIDS" --label "${LABEL}-A"
  BA_RC=$?
  set -e
  echo "baseline_exit=$BA_RC (1 = zero allows; still OK)"

  SUM_ARGS=(--label "$LABEL" --qids "$QIDS" --survivors "$SURVIVORS" --md "$BATCH_MD")
  if [[ "$INCLUDE_CASE_NOTE" -eq 1 ]]; then
    SUM_ARGS+=(--include-case-note)
  fi
  python3 "$LAB/batch_summarize_a.py" "${SUM_ARGS[@]}"
}

run_stage_b() {
  echo "========== STAGE B: judge survivors (max=$MAX_JUDGE) =========="
  if [[ ! -f "$SURVIVORS" ]]; then
    echo "ERROR: missing $SURVIVORS — run Stage A first" >&2
    exit 2
  fi

  mapfile -t NAMES < <(python3 -c "
import json
from pathlib import Path
data = json.loads(Path(r'''$SURVIVORS''').read_text())
rows = [r for r in data.get('survivors') or [] if r.get('stage_b')]
for r in rows[: int('''$MAX_JUDGE''')]:
    print(r['name'])
")
  TODO=()
  for n in "${NAMES[@]+"${NAMES[@]}"}"; do
    [[ -z "${n:-}" ]] && continue
    TODO+=("$n")
  done
  if [[ ${#TODO[@]} -eq 0 ]]; then
    echo "No Stage-B survivors (all blocked or CASE_NOTE-only)."
    echo "Next: evolve --mode explore --merge, then Stage A again."
    exit 0
  fi

  echo "Will judge ${#TODO[@]} factors: ${TODO[*]}"
  HIST="$LAB/lab/BATCH-HISTORY.md"
  if [[ ! -f "$HIST" ]]; then
    printf '%s\n' "# Batch Stage B history" "" \
      "| UTC | Label | Factor | Soft judge sum | Notes |" \
      "|-----|-------|--------|----------------|-------|" >"$HIST"
  fi
  UTC="$(date -u +%Y-%m-%dT%H:%MZ)"
  rm -f "$LAB/lab/BATCH-HIT.txt"

  for name in "${TODO[@]}"; do
    echo "----- promote + probe $name -----"
    python3 "$LAB/promote-factor.py" "$name" || continue
    set +e
    bash "$LAB/probe-and-judge.sh" --label "${LABEL}-B-${name}" --qids "$JUDGE_QIDS"
    RC=$?
    set -e
    SUM="$(python3 -c "
from pathlib import Path
hist = Path('miner-lab/lab/JUDGE-HISTORY.md')
label = '''${LABEL}-B-${name}'''
rows = []
if hist.is_file():
    for line in hist.read_text(encoding='utf-8').splitlines():
        if f'| {label} |' not in line:
            continue
        parts = [p.strip() for p in line.strip('|').split('|')]
        if len(parts) >= 4:
            try:
                rows.append(int(parts[3]))
            except ValueError:
                pass
print(sum(rows) if rows else 0)
")"
    NOTE="rc=$RC"
    [[ "$SUM" -gt 0 ]] && NOTE="SCORE_HIT $NOTE"
    echo "| $UTC | $LABEL | $name | $SUM | $NOTE |" >>"$HIST"
    echo "factor=$name soft_judge_sum=$SUM"
    if [[ "$SUM" -gt 0 ]]; then
      echo "=== HIT: $name judge_sum=$SUM — submit candidate ==="
      echo "$name" >"$LAB/lab/BATCH-HIT.txt"
    fi
  done

  {
    echo ""
    echo "## Stage B ($UTC / $LABEL)"
    echo ""
    echo "- Judged: ${#TODO[@]}"
    echo "- See lab/BATCH-HISTORY.md"
  } >>"$BATCH_MD"

  echo "========== STAGE B done =========="
  if [[ -f "$LAB/lab/BATCH-HIT.txt" ]]; then
    echo "Submit candidate: $(cat "$LAB/lab/BATCH-HIT.txt")"
  else
    echo "No judge>0 in this batch."
  fi
}

case "$STAGE" in
  a|A) run_stage_a ;;
  b|B) run_stage_b ;;
  all)
    run_stage_a
    run_stage_b
    ;;
  *) echo "STAGE must be a|b|all" >&2; exit 2 ;;
esac
