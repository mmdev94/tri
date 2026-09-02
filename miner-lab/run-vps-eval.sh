#!/usr/bin/env bash
# VPS miner-lab runner: health → optional guard probe → tri-check eval → detailed logs.
#
# Usage (from repo root or miner-lab/):
#   bash miner-lab/run-vps-eval.sh
#   bash miner-lab/run-vps-eval.sh --submission miner-lab/submission.json
#   bash miner-lab/run-vps-eval.sh --guard-only
#   bash miner-lab/run-vps-eval.sh --local          # local Halo override (needs serve_halo_guard)
#   bash miner-lab/run-vps-eval.sh --skip-guard-probe
#   bash miner-lab/run-vps-eval.sh --label v2-archival
#
# Outputs:
#   results/miner-lab/runs/<timestamp>[-label]/   # full logs (gitignored)
#   results/miner-lab/LATEST -> that run
#   miner-lab/shared/LATEST-SUMMARY.md + HISTORY.md  # shareable scores

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/miner-lab"
TRI_CHECK="$ROOT/tri-check"
RESULTS_ROOT="$ROOT/results/miner-lab"
SHARED="$LAB/shared"

SUBMISSION="$LAB/submission.json"
# Prefer newest synced challenge pack; else tri-check sample rubric (often stale).
QUESTIONS=""
if [[ -d "$LAB/challenges" ]]; then
  QUESTIONS="$(ls -1t "$LAB"/challenges/*-questions.json 2>/dev/null | head -n1 || true)"
fi
if [[ -z "$QUESTIONS" || ! -f "$QUESTIONS" ]]; then
  QUESTIONS="$TRI_CHECK/data/questions.json"
fi
LABEL=""
MODE="chutes" # chutes | local
GUARD_ONLY=0
SKIP_GUARD_PROBE=0
VERBOSE=1
GROUND_TRUTH=0

INPUT_GUARD_URL="${HALO_CLASSIFY_URL:-https://astroboi-halo-guard.chutes.ai/v1/classify}"
INPUT_GUARD_MODEL="${HALO_CLASSIFY_MODEL:-halo-guard}"
# Phase-3 Halo output guard (HF Halo0.8B-outputguard-v1 / chute astroboi-halo-output-guard).
# Older HaloQwen chute: https://astroboi-haloqwen-output-guard.chutes.ai/v1/classify
OUTPUT_GUARD_URL="${HALO_OUTPUT_CLASSIFY_URL:-https://astroboi-halo-output-guard.chutes.ai/v1/classify}"
OUTPUT_GUARD_MODEL="${HALO_OUTPUT_CLASSIFY_MODEL:-halo-output-guard}"

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --submission) SUBMISSION="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; shift 2 ;;
    --questions) QUESTIONS="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --local) MODE="local"; shift ;;
    --guard-only) GUARD_ONLY=1; shift ;;
    --skip-guard-probe) SKIP_GUARD_PROBE=1; shift ;;
    --ground-truth) GROUND_TRUTH=1; shift ;;
    --quiet) VERBOSE=0; shift ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ ! -f "$SUBMISSION" ]]; then
  echo "ERROR: submission not found: $SUBMISSION" >&2
  exit 1
fi

# Load env (repo root then tri-check; do not override already-set vars)
set -a
[[ -f "$ROOT/.env" ]] && . "$ROOT/.env"
[[ -f "$TRI_CHECK/.env" ]] && . "$TRI_CHECK/.env"
set +a

OPENCLAW_URL="${OPENCLAW_URL:-http://localhost:18789}"
JUDGE_URL="${JUDGE_URL:-http://localhost:8080}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_ID="$TS"
[[ -n "$LABEL" ]] && RUN_ID="${TS}-${LABEL}"
RUN_DIR="$RESULTS_ROOT/runs/$RUN_ID"
mkdir -p "$RUN_DIR" "$SHARED" "$RESULTS_ROOT"

cp -f "$SUBMISSION" "$RUN_DIR/submission.json"

GIT_SHA="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
HOST="$(hostname -s 2>/dev/null || hostname)"

META_JSON="$RUN_DIR/meta.json"
cat >"$META_JSON" <<EOF
{
  "run_id": "$RUN_ID",
  "utc": "$TS",
  "hostname": "$HOST",
  "mode": "$MODE",
  "git": "$GIT_SHA",
  "submission": "$SUBMISSION",
  "openclaw_url": "$OPENCLAW_URL",
  "judge_url": "$JUDGE_URL",
  "ground_truth_enabled": $GROUND_TRUTH
}
EOF

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$RUN_DIR/console.log"; }

log "=== miner-lab run $RUN_ID ==="
log "repo=$ROOT host=$HOST git=$GIT_SHA mode=$MODE"
log "submission=$SUBMISSION"
log "questions=$QUESTIONS"

# --- health ---
health_check() {
  local name="$1" url="$2"
  if curl -sf --max-time 10 "$url" >/dev/null; then
    log "HEALTH ok  $name ($url)"
    return 0
  fi
  log "HEALTH FAIL $name ($url)"
  return 1
}

HC_FAIL=0
health_check "openclaw" "${OPENCLAW_URL%/}/health" || HC_FAIL=1
health_check "judge" "${JUDGE_URL%/}/health" || HC_FAIL=1
if [[ "$HC_FAIL" -ne 0 && "$GUARD_ONLY" -eq 0 ]]; then
  log "ERROR: services unhealthy. Start with: bash docker-up.sh"
  exit 1
fi

# --- validate template length / placeholder via node if available ---
if command -v node >/dev/null 2>&1; then
  node - "$SUBMISSION" <<'NODE' | tee -a "$RUN_DIR/console.log"
const fs = require("fs");
// argv: [node, "-", submissionPath] when script is stdin ("-")
const path = process.argv[2] || process.argv[1];
const body = JSON.parse(fs.readFileSync(path, "utf8"));
const prompt = body.prompt || "";
const re = /\{\{\s*objective\s*\}\}/gi;
const matches = prompt.match(re) || [];
console.log(`[validate] prompt_len=${prompt.length} max=2000 placeholders=${matches.length}`);
if (!prompt.trim()) { console.error("[validate] FAIL empty prompt"); process.exit(1); }
if (prompt.length > 2000) { console.error("[validate] FAIL over 2000 chars"); process.exit(1); }
if (matches.length !== 1) { console.error("[validate] FAIL need exactly one {{objective}}"); process.exit(1); }
const nonEn = /[\u3400-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]/.test(prompt);
if (nonEn) console.warn("[validate] WARN CJK characters detected — English-only challenge rule");
console.log("[validate] OK");
NODE
fi

# Build a short probe text: expand with Q1 objective if questions file exists
PROBE_QUERY="$RUN_DIR/probe_query.txt"
python3 - <<PY
import json
from pathlib import Path
sub = json.loads(Path("$SUBMISSION").read_text())
template = sub["prompt"]
obj = "compliance documentation sample objective for guard probe only"
qpath = Path("$QUESTIONS")
if qpath.exists():
    data = json.loads(qpath.read_text())
    rows = data if isinstance(data, list) else data.get("questions", [])
    for row in rows:
        qid = row.get("question_id") or row.get("id")
        if qid == "Q1" and row.get("objective"):
            obj = row["objective"]
            break
import re
expanded = re.sub(r"\{\{\s*objective\s*\}\}", obj, template, count=1, flags=re.I)
Path("$PROBE_QUERY").write_text(expanded, encoding="utf-8")
print(f"[probe] expanded_len={len(expanded)}")
PY

# --- guard probes ---
if [[ "$SKIP_GUARD_PROBE" -eq 0 ]]; then
  cd "$TRI_CHECK"
  if [[ ! -d node_modules ]]; then
    log "pnpm install in tri-check…"
    pnpm install
  fi

  QUERY="$(cat "$PROBE_QUERY")"
  GUARD_LOG="$RUN_DIR/guard-probe.log"

  if [[ "$MODE" == "local" ]]; then
    log "GUARD probe local INPUT…"
    set +e
    pnpm guard-probe -- --query "$QUERY" --local --role input --verbose \
      2>&1 | tee -a "$GUARD_LOG" "$RUN_DIR/console.log"
    set -e
    log "GUARD probe local OUTPUT (sample assistant text)…"
    set +e
    pnpm guard-probe -- --query "CASE_FILE_START archival notes for review." --local --role output --verbose \
      2>&1 | tee -a "$GUARD_LOG" "$RUN_DIR/console.log"
    set -e
  else
    if [[ -z "${CHUTES_API_KEY:-}" ]]; then
      log "WARN: CHUTES_API_KEY empty — skip --halo-direct probes; OpenClaw path may still work if key is elsewhere"
    else
      log "GUARD probe Chutes INPUT ($INPUT_GUARD_URL)…"
      set +e
      pnpm guard-probe -- --query "$QUERY" --halo-direct --role input \
        --classify-url "$INPUT_GUARD_URL" --classify-model "$INPUT_GUARD_MODEL" --verbose \
        2>&1 | tee -a "$GUARD_LOG" "$RUN_DIR/console.log"
      set -e

      log "GUARD probe Chutes OUTPUT ($OUTPUT_GUARD_URL)…"
      set +e
      pnpm guard-probe -- --query "CASE_FILE_START archival notes for review." --halo-direct --role output \
        --classify-url "$OUTPUT_GUARD_URL" --classify-model "$OUTPUT_GUARD_MODEL" --verbose \
        2>&1 | tee -a "$GUARD_LOG" "$RUN_DIR/console.log"
      set -e
    fi
  fi
fi

if [[ "$GUARD_ONLY" -eq 1 ]]; then
  log "GUARD_ONLY set — skipping full eval"
  ln -sfn "runs/$RUN_ID" "$RESULTS_ROOT/LATEST"
  log "Done. Artifacts: $RUN_DIR"
  exit 0
fi

# --- full eval ---
cd "$TRI_CHECK"
if [[ ! -d node_modules ]]; then
  log "pnpm install in tri-check…"
  pnpm install
fi

EVAL_ARGS=(--submission "$SUBMISSION" --questions "$QUESTIONS" --out "$RUN_DIR/report.json")
[[ "$VERBOSE" -eq 1 ]] && EVAL_ARGS+=(--verbose)
[[ "$MODE" == "local" ]] && EVAL_ARGS+=(--local)

if [[ "$GROUND_TRUTH" -eq 1 ]]; then
  export TRI_CHECK_GROUND_TRUTH_ENABLED=1
  log "TRI_CHECK_GROUND_TRUTH_ENABLED=1 (Q7–Q12 secrets merge)"
fi

log "EVAL starting: pnpm eval ${EVAL_ARGS[*]}"
set +e
pnpm eval "${EVAL_ARGS[@]}" 2>&1 | tee -a "$RUN_DIR/console.log"
EVAL_RC=${PIPESTATUS[0]}
set -e
log "EVAL exit_code=$EVAL_RC"

if [[ ! -f "$RUN_DIR/report.json" ]]; then
  log "ERROR: report.json missing"
  exit 1
fi

python3 "$LAB/summarize_report.py" \
  --report "$RUN_DIR/report.json" \
  --run-dir "$RUN_DIR" \
  --run-id "$RUN_ID" \
  --submission "$SUBMISSION" \
  --shared-dir "$SHARED" \
  --mode "$MODE" \
  --hostname "$HOST" \
  --git "$GIT_SHA" \
  2>&1 | tee -a "$RUN_DIR/console.log"

ln -sfn "runs/$RUN_ID" "$RESULTS_ROOT/LATEST"

log "=== complete ==="
log "Full run:     $RUN_DIR"
log "Summary:      $RUN_DIR/SUMMARY.md"
log "Shareable:    $SHARED/LATEST-SUMMARY.md"
log "History:      $SHARED/HISTORY.md"
log "Symlink:      $RESULTS_ROOT/LATEST"

exit "$EVAL_RC"
