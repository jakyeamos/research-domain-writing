#!/usr/bin/env python3
from __future__ import annotations

import dis
import sys
import trace
from pathlib import Path
from types import CodeType

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "build" / "pre-cr-python.lcov"
COVERAGE_FILES = [
    ROOT / "scripts" / "sync-package-assets.py",
    ROOT / "src" / "rdw" / "adapters" / "fixture.py",
    ROOT / "src" / "rdw" / "artifact_validation.py",
    ROOT / "src" / "rdw" / "cli.py",
    ROOT / "src" / "rdw" / "contracts.py",
    ROOT / "src" / "rdw" / "diff_qa.py",
    ROOT / "src" / "rdw" / "diff_qa_compare.py",
    ROOT / "src" / "rdw" / "diff_qa_normalize.py",
    ROOT / "src" / "rdw" / "diff_qa_reporting.py",
    ROOT / "src" / "rdw" / "diff_qa_support.py",
    ROOT / "src" / "rdw" / "diff_qa_validation.py",
    ROOT / "src" / "rdw" / "domain.py",
    ROOT / "src" / "rdw" / "execution.py",
    ROOT / "src" / "rdw" / "install.py",
    ROOT / "src" / "rdw" / "lifecycle.py",
    ROOT / "src" / "rdw" / "planner.py",
    ROOT / "src" / "rdw" / "resources.py",
    ROOT / "src" / "rdw" / "schema_export.py",
    ROOT / "src" / "rdw" / "validation.py",
    ROOT / "src" / "rdw" / "yaml_io.py",
]


def _executable_lines(source: str, filename: str) -> set[int]:
    def code_lines(code: CodeType) -> set[int]:
        lines = {line for _, line in dis.findlinestarts(code) if line is not None and line > 0}
        for constant in code.co_consts:
            if isinstance(constant, CodeType):
                lines.update(code_lines(constant))
        return lines

    return code_lines(compile(source, filename, "exec"))


def _write_lcov(counts: dict[tuple[str, int], int]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        for file_path in COVERAGE_FILES:
            relative_path = file_path.relative_to(ROOT).as_posix()
            executable = sorted(
                _executable_lines(file_path.read_text(encoding="utf-8"), str(file_path))
            )
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
