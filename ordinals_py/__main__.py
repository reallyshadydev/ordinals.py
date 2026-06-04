"""python3 -m ordinals_py — use project .venv when embit 0.8 is not on system Python."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_VENV_PY = _ROOT / ".venv" / "bin" / "python"


def _in_project_venv() -> bool:
    venv = _ROOT / ".venv"
    return os.environ.get("VIRTUAL_ENV") == str(venv.resolve())


def _ensure_venv() -> None:
    if _in_project_venv():
        return
    if not _VENV_PY.is_file():
        return
    try:
        from embit.misc import const  # noqa: F401

        return
    except ModuleNotFoundError:
        pass
    os.chdir(_ROOT)
    os.execv(
        str(_VENV_PY),
        [str(_VENV_PY), "-m", "ordinals_py", *sys.argv[1:]],
    )


_ensure_venv()

try:
    from embit.misc import const  # noqa: F401
except ModuleNotFoundError:
    print(
        "embit>=0.8 is required.\n"
        "  cd /root/ordinals-py && ./run.sh wallet new\n"
        "  # or: python3 -m venv .venv && .venv/bin/pip install embit==0.8.0\n"
        "  #     .venv/bin/python -m ordinals_py wallet new",
        file=sys.stderr,
    )
    raise SystemExit(1) from None

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
