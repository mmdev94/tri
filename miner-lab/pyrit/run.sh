#!/usr/bin/env bash
# Run PyRIT miner-lab filter with the local venv.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYRIT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PYRIT_DIR/.venv"
PY="$VENV/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "Creating venv + installing deps…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -U pip
  "$VENV/bin/pip" install -r "$PYRIT_DIR/requirements.txt"
fi

# load .env without exporting everything via set -a if missing
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
if [[ -f "$ROOT/tri-check/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/tri-check/.env"
  set +a
fi

export PYTHONPATH="$PYRIT_DIR:${PYTHONPATH:-}"
cd "$ROOT"
exec "$PY" "$PYRIT_DIR/run_filter.py" "$@"
