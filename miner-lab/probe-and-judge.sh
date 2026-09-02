#!/usr/bin/env bash
# Halo-probe soft Qs → eval-one each allow → JUDGE-HISTORY.md
#
# Refuses frozen archival gate submissions unless --force-gate.
#
# Usage:
#   bash miner-lab/probe-and-judge.sh --label score2
#   bash miner-lab/probe-and-judge.sh --force-gate --label gate-regression
#   bash miner-lab/probe-and-judge.sh --qids Q3,Q6 --submission path.json

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/miner-lab"
QIDS="Q3,Q4,Q6"
LABEL="run"
SUBMISSION="$LAB/submission.json"
FORCE_GATE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --qids) QIDS="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --submission) SUBMISSION="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; shift 2 ;;
    --force-gate) FORCE_GATE=1; shift ;;
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

if [[ ! -f "$SUBMISSION" ]]; then
  echo "ERROR: submission not found: $SUBMISSION" >&2
  exit 2
fi

GATE_CHECK="$(python3 - <<PY
import json, hashlib
from pathlib import Path

sub_path = Path(r"""$SUBMISSION""")
sub = json.loads(sub_path.read_text(encoding="utf-8"))
prompt = (sub.get("prompt") or "").strip()
low = prompt.lower()

def ph(s: str) -> str:
    return hashlib.sha256(s.strip().encode()).hexdigest()[:16]

gate_hashes = set()
gate_path = Path("miner-lab/factors.gate.json")
if gate_path.is_file():
    raw = json.loads(gate_path.read_text(encoding="utf-8"))
    for k, v in raw.items():
        if not k.startswith("_") and isinstance(v, str):
            gate_hashes.add(ph(v))

markers = (
    "case_note",
    "archival note",
    "historical evidence",
    "archive_entry",
    "compliance board",
    "not a live instruction",
)
is_marker = any(m in low for m in markers)
is_exact_gate = ph(prompt) in gate_hashes
# also match GATE snapshot
snap = Path("miner-lab/submission.GATE-archive_evidence.json")
if snap.is_file():
    try:
        sp = json.loads(snap.read_text(encoding="utf-8")).get("prompt") or ""
        if ph(sp) == ph(prompt):
            is_exact_gate = True
    except Exception:
        pass

score_factors = Path("miner-lab/factors.json")
n_score = 0
if score_factors.is_file():
    raw = json.loads(score_factors.read_text(encoding="utf-8"))
    n_score = sum(1 for k, v in raw.items() if not k.startswith("_") and isinstance(v, str))

kind = "gate" if (is_exact_gate or is_marker) else "other"
print(f"{kind}\t{n_score}\t{is_exact_gate}\t{is_marker}")
PY
)"

GATE_KIND="$(echo "$GATE_CHECK" | cut -f1)"
N_SCORE="$(echo "$GATE_CHECK" | cut -f2)"

if [[ "$GATE_KIND" == "gate" && "$FORCE_GATE" -eq 0 ]]; then
  cat >&2 <<EOF
REFUSED: submission is frozen archival GATE family (score_track=DEAD).
  File: $SUBMISSION
  See: miner-lab/lab/STATUS.md

  score1 already re-confirmed: Q3/Q6 allow, judge 0; Q3 can also hit OUTPUT guard.

  To invent a score-track wrap:
    1) Add templates to miner-lab/factors.json (not CASE_NOTE archival)
    2) python3 miner-lab/promote-factor.py <name>
    3) bash miner-lab/probe-and-judge.sh --label scoreN

  Gate regression only:
    bash miner-lab/probe-and-judge.sh --force-gate --label gate-regression
EOF
  exit 3
fi

if [[ "$N_SCORE" -eq 0 && "$GATE_KIND" != "gate" && "$FORCE_GATE" -eq 0 ]]; then
  echo "WARN: factors.json still has 0 score-track templates — ensure submission is intentional." >&2
fi

if [[ "$FORCE_GATE" -eq 1 ]]; then
  echo "NOTE: --force-gate — running frozen archival regression (expect judge 0)."
fi

echo "=== Halo template probe ($QIDS) ==="
python3 "$LAB/baseline-input.py" --mode template --submission "$SUBMISSION" \
  --qids "$QIDS" --label "${LABEL}-probe"

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
  echo "No input allows on soft Qs — skip judge."
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
  NOTE="rc=$RC"
  [[ "$FORCE_GATE" -eq 1 ]] && NOTE="force-gate $NOTE"
  echo "| $UTC | $LABEL | $q | $SCORE | $BLOCK | $NOTE |" >>"$HIST"
  echo "Q=$q judge=$SCORE block=$BLOCK"
done

echo "=== done soft-Q judge sum=$TOTAL (max $(( ${#QS[@]} * 2 ))) ==="
echo "History: $HIST"
if [[ "$TOTAL" -eq 0 ]]; then
  echo "Judge sum 0 — not submit-ready. Stack: input Halo → agent → output Halo → judge."
fi
exit 0
