#!/usr/bin/env python3
"""Entry point — re-execs with .venv when present (needs embit>=0.8)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / "bin" / "python"


def _in_project_venv() -> bool:
    return os.environ.get("VIRTUAL_ENV") == str((ROOT / ".venv").resolve())


def _ensure_venv() -> None:
    if _in_project_venv():
        return
    if not VENV_PY.is_file():
        return
    try:
        from embit.misc import const  # noqa: F401

        return
    except ModuleNotFoundError:
        pass
    os.chdir(ROOT)
    os.execv(str(VENV_PY), [str(VENV_PY), str(ROOT / "ordinals.py"), *sys.argv[1:]])


_ensure_venv()

try:
    from embit.misc import const  # noqa: F401
except ModuleNotFoundError:
    print(
        "embit>=0.8 is required. From /root/ordinals-py run:\n"
        "  python3 -m venv .venv && .venv/bin/pip install embit==0.8.0\n"
        "  ./ordinals.py wallet new\n"
        "Or: .venv/bin/python -m ordinals_py wallet new",
        file=sys.stderr,
    )
    raise SystemExit(1) from None

from ordinals_py.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
