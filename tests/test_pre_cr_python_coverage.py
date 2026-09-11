from __future__ import annotations

import importlib.util
import sys
import trace
from pathlib import Path


def test_lcov_uses_bytecode_lines_and_real_branch_hits(tmp_path: Path) -> None:
    adapter_path = Path(__file__).resolve().parents[1] / "scripts/run-pre-cr-python-tests.py"
    spec = importlib.util.spec_from_file_location("pre_cr_python_fixture", adapter_path)
    assert spec is not None and spec.loader is not None
    adapter = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = adapter
    spec.loader.exec_module(adapter)

    source = (
        "PAIRS = (\n"
        '    ("a", "b"),\n'
        '    ("c", "d"),\n'
        ")\n"
        "def choose(flag):\n"
        "    if flag:\n"
        "        return 1\n"
        "    return 2\n"
        "choose(True)\n"
    )
    path = tmp_path / "fixture.py"
    path.write_text(source)
    tracer = trace.Trace(count=True, trace=False)
    namespace = {"__file__": str(path), "__name__": "coverage_fixture"}
    tracer.runctx(compile(source, str(path), "exec"), namespace, namespace)
    vars(adapter).update(
        ROOT=tmp_path, OUTPUT_PATH=tmp_path / "coverage.lcov", COVERAGE_FILES=[path]
    )
    adapter._write_lcov(tracer.results().counts)
    records = adapter.OUTPUT_PATH.read_text().splitlines()
    hits = {
        int(line.split(":")[1].split(",")[0]): int(line.split(",")[1])
        for line in records
        if line.startswith("DA:")
    }
    assert 2 not in hits and 3 not in hits  # Constant tuple continuation has no bytecode.
    assert hits[7] > 0  # The selected branch really ran.
    assert hits[8] == 0  # The executable unselected branch stays uncovered.
    assert hits[9] > 0  # Module-level execution is measured too.
