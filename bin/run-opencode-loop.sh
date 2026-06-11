#!/usr/bin/env bash
# Run the portable opencode loop runner from this repository.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -f "./venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ./venv/bin/activate
  PYTHON_BIN="python"
elif [[ -f "./.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ./.venv/bin/activate
  PYTHON_BIN="python"
fi

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m loops_opencode.cli "$@"
