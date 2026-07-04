#!/usr/bin/env python3
"""Compatibility wrapper for `rdw validate-packet`."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate-packet.py <packet.yaml>", file=sys.stderr)
        return 2
    from rdw.cli import main as rdw_main

    return rdw_main(["validate-packet", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
