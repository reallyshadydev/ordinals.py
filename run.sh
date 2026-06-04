#!/usr/bin/env bash
# Run ordinals_py with the project venv (embit 0.8+).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  echo "Creating .venv and installing embit==0.8.0…"
  python3 -m venv .venv
  .venv/bin/pip install -U pip -q
  .venv/bin/pip install embit==0.8.0 -q
fi
exec .venv/bin/python -m ordinals_py "$@"
