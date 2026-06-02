#!/usr/bin/env python3
"""Entry point: python3 ordinals.py mint <address> <file> (same argv as node ordinals.js)."""

from ordinals_py.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
