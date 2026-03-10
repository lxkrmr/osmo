#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"

if [ ! -x "$PY" ]; then
  python3 -m venv "$ROOT/.venv"
fi

"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r "$ROOT/requirements.txt"

echo "Bootstrap complete."
echo "Next steps:"
echo "  1) direnv allow"
echo "  2) ./scripts/install-git-hooks.sh"
echo "  3) ./scripts/smoke-test.sh"
