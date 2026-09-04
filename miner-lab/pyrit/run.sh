#!/usr/bin/env bash
# PyRIT miner-lab entrypoint.
#   bash miner-lab/pyrit/run.sh …                 # filter (Halo ± stack)
#   bash miner-lab/pyrit/run.sh filter …
#   bash miner-lab/pyrit/run.sh attack …          # advanced attacks
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

CMD="filter"
if [[ "${1:-}" == "attack" || "${1:-}" == "filter" || "${1:-}" == "send" ]]; then
  CMD="$1"
  shift
fi

case "$CMD" in
  attack)
    exec "$PY" "$PYRIT_DIR/run_attacks.py" "$@"
    ;;
  send)
    exec "$PY" "$PYRIT_DIR/pyrit_send.py" "$@"
    ;;
  filter|*)
    exec "$PY" "$PYRIT_DIR/run_filter.py" "$@"
    ;;
esac
