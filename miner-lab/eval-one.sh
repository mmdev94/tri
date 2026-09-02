#!/usr/bin/env bash
# One-question full eval after input allow (recommended vision).
#
# Usage:
#   bash miner-lab/eval-one.sh Q6
#   bash miner-lab/eval-one.sh Q6 --submission miner-lab/submission.json
#   bash miner-lab/eval-one.sh Q3 --label q3-try1

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/miner-lab"
TRI_CHECK="$ROOT/tri-check"

QID=""
SUBMISSION="$LAB/submission.json"
LABEL=""
QUESTIONS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --submission) SUBMISSION="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; shift 2 ;;
    --questions) QUESTIONS="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      if [[ -z "$QID" ]]; then QID="$1"; shift
      else echo "Unknown arg: $1" >&2; exit 2
      fi
      ;;
  esac
done

if [[ -z "$QID" ]]; then
  echo "Usage: bash miner-lab/eval-one.sh Q6 [--label tag]" >&2
  exit 2
fi

if [[ -z "$QUESTIONS" ]]; then
  QUESTIONS="$(ls -1t "$LAB"/challenges/*-questions.json 2>/dev/null | head -n1 || true)"
fi
if [[ -z "$QUESTIONS" || ! -f "$QUESTIONS" ]]; then
  QUESTIONS="$TRI_CHECK/data/questions.json"
fi

set -a
[[ -f "$ROOT/.env" ]] && . "$ROOT/.env"
[[ -f "$TRI_CHECK/.env" ]] && . "$TRI_CHECK/.env"
set +a

TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_ID="${TS}-one-${QID}${LABEL:+-$LABEL}"
RUN_DIR="$ROOT/results/miner-lab/runs/$RUN_ID"
mkdir -p "$RUN_DIR"

PROMPT_FILE="$RUN_DIR/expanded_prompt.txt"
python3 - <<PY
import json, re
from pathlib import Path
sub = json.loads(Path("$SUBMISSION").read_text())
template = sub["prompt"]
rows = json.loads(Path("$QUESTIONS").read_text())
rows = rows if isinstance(rows, list) else rows.get("questions", [])
obj = None
for r in rows:
    if (r.get("question_id") or r.get("id")) == "$QID":
        obj = r.get("objective")
        break
if not obj:
    raise SystemExit("Question $QID not found in $QUESTIONS")
expanded = re.sub(r"\{\{\s*objective\s*\}\}", obj, template, count=1, flags=re.I)
Path("$PROMPT_FILE").write_text(expanded, encoding="utf-8")
print(f"[eval-one] q=$QID expanded_len={len(expanded)}")
print(f"[eval-one] objective_preview={obj[:80]!r}")
PY

cp -f "$SUBMISSION" "$RUN_DIR/submission.json"
PROMPT="$(cat "$PROMPT_FILE")"

# Prefer nvm Node 22+ over Cursor-bundled Node 20
if [[ -d "$HOME/.nvm/versions/node" ]]; then
  NEWEST_NODE="$(ls -1d "$HOME/.nvm/versions/node"/v*/bin 2>/dev/null | sort -V | tail -n1 || true)"
  if [[ -n "$NEWEST_NODE" ]]; then
    export PATH="$NEWEST_NODE:$PATH"
  fi
fi

cd "$TRI_CHECK"
if [[ ! -d node_modules ]]; then
  if command -v pnpm >/dev/null 2>&1; then
    pnpm install || npm install
  else
    npm install
  fi
fi

echo "[eval-one] run_dir=$RUN_DIR node=$(command -v node) $(node -v 2>/dev/null || true)"
set +e
if command -v pnpm >/dev/null 2>&1 && pnpm -v >/dev/null 2>&1; then
  pnpm eval --question "$QID" --prompt "$PROMPT" --questions "$QUESTIONS" \
    --out "$RUN_DIR/report.json" --verbose \
    2>&1 | tee "$RUN_DIR/console.log"
  RC=${PIPESTATUS[0]}
else
  npm run eval -- --question "$QID" --prompt "$PROMPT" --questions "$QUESTIONS" \
    --out "$RUN_DIR/report.json" --verbose \
    2>&1 | tee "$RUN_DIR/console.log"
  RC=${PIPESTATUS[0]}
fi
set -e

if [[ -f "$RUN_DIR/report.json" ]]; then
  python3 "$LAB/summarize_report.py" \
    --report "$RUN_DIR/report.json" \
    --run-dir "$RUN_DIR" \
    --run-id "$RUN_ID" \
    --submission "$SUBMISSION" \
    --shared-dir "$LAB/shared" \
    --mode "chutes-one" \
    --hostname "$(hostname -s 2>/dev/null || hostname)" \
    --git "$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)" \
    2>&1 | tee -a "$RUN_DIR/console.log"
fi

ln -sfn "runs/$RUN_ID" "$ROOT/results/miner-lab/LATEST"
echo "[eval-one] exit=$RC  summary=$RUN_DIR/SUMMARY.md"
exit "$RC"
