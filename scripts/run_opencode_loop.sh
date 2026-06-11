#!/usr/bin/env bash
# Objetivo: ejecutar el runner de /loop usando el entorno virtual local.
# Inputs: argumentos para scripts/opencode_loop_runner.py.
# Output: sesiones opencode iterativas y logs bajo .opencode/loop/runs/.
# Cómo correr:
#   ./scripts/run_opencode_loop.sh "objetivo largo"
#   ./scripts/run_opencode_loop.sh --continue
# Side-effects: activa ./venv y ejecuta opencode run en sesiones nuevas.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f "./venv/bin/activate" ]]; then
  echo "No existe ./venv/bin/activate" >&2
  exit 1
fi

source ./venv/bin/activate
python scripts/opencode_loop_runner.py "$@"
