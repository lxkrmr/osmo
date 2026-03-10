#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "Missing local venv: $PY" >&2
  echo "Run first: ./scripts/bootstrap.sh" >&2
  exit 1
fi

git -C "$ROOT" config core.hooksPath .githooks
chmod +x "$ROOT/.githooks/pre-commit"

echo "Installed local git hooks (core.hooksPath=.githooks)"
echo "pre-commit now runs: ./scripts/smoke-test.sh"
echo "Next: ./scripts/smoke-test.sh"
