#!/usr/bin/env bash
# Run Halo-input and/or OpenClaw promptfoo evals (P3-007 Q1–Q6 × wraps).
#
# Usage (repo root):
#   bash miner-lab/promptfoo/run.sh              # both, if OpenClaw is up
#   bash miner-lab/promptfoo/run.sh --input-only
#   bash miner-lab/promptfoo/run.sh --stack-only
#   bash miner-lab/promptfoo/run.sh --qid Q5     # --filter-pattern Q5

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PF="$ROOT/miner-lab/promptfoo"
MODE="both"
FILTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input-only) MODE="input"; shift ;;
    --stack-only) MODE="stack"; shift ;;
    --qid) FILTER="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 2 ;;
  esac
done

cd "$ROOT"
set -a
[[ -f .env ]] && . ./.env
[[ -f tri-check/.env ]] && . ./tri-check/.env
[[ -f .env.tri-claw ]] && . ./.env.tri-claw
set +a

if [[ -z "${OPENCLAW_URL:-}" ]]; then
  export OPENCLAW_URL="http://127.0.0.1:18789/v1/chat/completions"
elif [[ "$OPENCLAW_URL" != */v1/chat/completions ]]; then
  export OPENCLAW_URL="${OPENCLAW_URL%/}/v1/chat/completions"
fi

# promptfoo Bearer uses OPENCLAW_GATEWAY_PASSWORD; allow TOKEN alias
if [[ -z "${OPENCLAW_GATEWAY_PASSWORD:-}" && -n "${OPENCLAW_GATEWAY_TOKEN:-}" ]]; then
  export OPENCLAW_GATEWAY_PASSWORD="$OPENCLAW_GATEWAY_TOKEN"
fi

python3 "$PF/build_tests.py"

FILTER_ARGS=()
if [[ -n "$FILTER" ]]; then
  FILTER_ARGS=(--filter-pattern "$FILTER")
fi

run_one() {
  local cfg="$1"
  echo "=== promptfoo $cfg ==="
  (cd "$PF" && npx --yes promptfoo@0.118.17 eval -c "$cfg" --no-cache "${FILTER_ARGS[@]}")
}

if [[ "$MODE" == "input" || "$MODE" == "both" ]]; then
  if [[ -z "${CHUTES_API_KEY:-}" ]]; then
    echo "ERROR: CHUTES_API_KEY missing" >&2
    exit 2
  fi
  run_one promptfooconfig.halo-input.yaml
fi

if [[ "$MODE" == "stack" || "$MODE" == "both" ]]; then
  if [[ "$MODE" == "both" ]]; then
    code="$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "${OPENCLAW_URL%/v1/chat/completions}/" || true)"
    if [[ "$code" == "000" ]]; then
      echo "OpenClaw not up (${OPENCLAW_URL}) — skip stack. Start claw then: bash miner-lab/promptfoo/run.sh --stack-only"
      exit 0
    fi
  fi
  if [[ -z "${OPENCLAW_GATEWAY_PASSWORD:-}" ]]; then
    echo "ERROR: OPENCLAW_GATEWAY_PASSWORD missing" >&2
    exit 2
  fi
  if [[ -z "${CHUTES_API_KEY:-}" ]]; then
    echo "ERROR: CHUTES_API_KEY missing (OpenClaw Chutes header)" >&2
    exit 2
  fi
  run_one promptfooconfig.openclaw.yaml
fi
