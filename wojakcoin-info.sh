#!/usr/bin/env bash
# Quick check: Wojakcoin RPC + ordinals-py config
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -U pip -q
  .venv/bin/pip install embit==0.8.0 -q
fi
exec .venv/bin/python -m ordinals_py info
