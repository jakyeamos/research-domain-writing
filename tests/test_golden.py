from __future__ import annotations

import os
from pathlib import Path

import pytest

from rdw.planner import TaskRequest, plan_task

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "golden"

REQUESTS = {
    "lis-leaderboard": "improve the copy on my LIS leaderboard",
    "album-blurb": "short album blurb about production",
    "api-feature": "explain the API feature for backend engineers",
    "idempotency": "explain idempotency keys",
}


@pytest.mark.parametrize("slug", sorted(REQUESTS))
def test_golden_contract_and_bundle(slug: str, tmp_path: Path) -> None:
    plan_task(TaskRequest(request=REQUESTS[slug]), tmp_path / slug, root=ROOT)
    contract = (tmp_path / slug / "task-contract.yaml").read_text(encoding="utf-8")
    bundle = (tmp_path / slug / "prompt-bundle.md").read_text(encoding="utf-8")

    golden_dir = GOLDEN / slug
    if os.environ.get("RDW_UPDATE_GOLDEN"):
        golden_dir.mkdir(parents=True, exist_ok=True)
        (golden_dir / "task-contract.yaml").write_text(contract, encoding="utf-8")
        (golden_dir / "prompt-bundle.md").write_text(bundle, encoding="utf-8")
        pytest.skip(f"regenerated golden for {slug}")

    assert contract == (golden_dir / "task-contract.yaml").read_text(encoding="utf-8")
    assert bundle == (golden_dir / "prompt-bundle.md").read_text(encoding="utf-8")
