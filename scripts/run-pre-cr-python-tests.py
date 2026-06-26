#!/usr/bin/env python3
from __future__ import annotations

import sys
import trace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "build" / "pre-cr-python.lcov"
COVERAGE_FILES = [
    ROOT / "scripts" / "validate-packet.py",
]


def _looks_executable(source: str) -> bool:
    stripped = source.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if stripped in {"{", "}", "(", ")", "[", "]"}:
        return False
    return not (stripped.startswith('"') and stripped.endswith(('",', '"')))


def _write_lcov(counts: dict[tuple[str, int], int]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        for file_path in COVERAGE_FILES:
            relative_path = file_path.relative_to(ROOT).as_posix()
            lines = file_path.read_text(encoding="utf-8").splitlines()
            executable = [
                line_number
                for line_number, line in enumerate(lines, start=1)
                if _looks_executable(line)
            ]
            if not executable:
                continue
            handle.write(f"SF:{relative_path}\n")
            hit_lines = 0
            for line_number in executable:
                hits = int(counts.get((str(file_path), line_number), 0))
                if hits > 0:
                    hit_lines += 1
                handle.write(f"DA:{line_number},{hits}\n")
            handle.write(f"LF:{len(executable)}\n")
            handle.write(f"LH:{hit_lines}\n")
            handle.write("end_of_record\n")


def main() -> int:
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.exec_prefix])
    exit_code = int(tracer.runfunc(pytest.main, ["-q"]))
    counts = tracer.results().counts
    _write_lcov(counts)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
