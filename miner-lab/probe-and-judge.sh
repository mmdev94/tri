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

dead_hashes = set()
for path in (Path("miner-lab/factors.gate.json"), Path("miner-lab/factors.killed.json")):
    if not path.is_file():
        continue
    raw = json.loads(path.read_text(encoding="utf-8"))
    for k, v in raw.items():
        if not k.startswith("_") and isinstance(v, str):
            dead_hashes.add(ph(v))

snap = Path("miner-lab/submission.GATE-archive_evidence.json")
if snap.is_file():
    try:
        sp = json.loads(snap.read_text(encoding="utf-8")).get("prompt") or ""
        dead_hashes.add(ph(sp))
    except Exception:
        pass

is_dead_hash = ph(prompt) in dead_hashes
# CASE_NOTE / near-ae family markers (score2c dead)
is_case_note_family = (
    "case_note" in low
    or ("archival note" in low and "historical evidence" in low)
    or ("compliance board" in low and "quoted evidence" in low)
)

score_factors = Path("miner-lab/factors.json")
n_score = 0
in_score = False
if score_factors.is_file():
    raw = json.loads(score_factors.read_text(encoding="utf-8"))
    for k, v in raw.items():
        if k.startswith("_") or not isinstance(v, str):
            continue
        n_score += 1
        if ph(v) == ph(prompt):
            in_score = True

# Refuse dead hashes always; refuse CASE_NOTE family when score track empty
# (allows intentional in-score mutants only while factors.json has entries).
kind = "other"
if is_dead_hash:
    kind = "dead"
elif is_case_note_family and n_score == 0:
    kind = "dead_family"
elif is_case_note_family and not in_score:
    kind = "dead_family"
print(f"{kind}\t{n_score}\t{is_dead_hash}\t{is_case_note_family}\t{in_score}")
PY
)"

GATE_KIND="$(echo "$GATE_CHECK" | cut -f1)"
N_SCORE="$(echo "$GATE_CHECK" | cut -f2)"

if [[ "$GATE_KIND" != "other" && "$FORCE_GATE" -eq 0 ]]; then
  cat >&2 <<EOF
REFUSED: submission is frozen CASE_NOTE / near-ae family (score_track=DEAD).
  kind=$GATE_KIND  file=$SUBMISSION
  See: miner-lab/lab/STATUS.md  (score2c: judge sum 0 even when output allows)

  Do NOT re-run ae_claims_bullets / archive_evidence.
  Add a NEW family to miner-lab/factors.json, then:
    python3 miner-lab/promote-factor.py <name>
    bash miner-lab/probe-and-judge.sh --label score3

  Gate regression only:
    bash miner-lab/probe-and-judge.sh --force-gate --label gate-regression
EOF
  exit 3
fi

if [[ "$N_SCORE" -eq 0 && "$FORCE_GATE" -eq 0 ]]; then
  cat >&2 <<EOF
REFUSED: factors.json has 0 active score templates (track empty after score2c).
  Stale submission.json will not be probed. Invent NEW factors first.
EOF
  exit 3
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
