from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "rdw_validate_packet", ROOT / "scripts" / "validate-packet.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sample_packet_validates_with_yaml_dependency() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-packet.py"),
            str(ROOT / "knowledge" / "basketball" / "jalen-brunson-2024-25.yaml"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "OK:" in result.stdout


def test_validator_reports_missing_required_fields() -> None:
    module = _load_validator_module()
    validate = cast(Callable[[dict[str, object]], list[str]], getattr(module, "validate"))

    errors = validate({"confidence_level": "high", "key_facts": ["known fact"]})

    assert "missing or empty required field: id" in errors


def test_validator_reports_invalid_confidence_and_empty_facts() -> None:
    module = _load_validator_module()
    validate = cast(Callable[[dict[str, object]], list[str]], getattr(module, "validate"))

    errors = validate(
        {
            "id": "packet",
            "domain": "basketball",
            "entity_type": "player",
            "entity_name": "Player",
            "key_facts": [],
            "source_notes": ["sample"],
            "confidence_level": "certain",
            "last_updated": "2026-06-26",
        }
    )

    assert "confidence_level must be high|medium|low" in errors
    assert "missing or empty required field: key_facts" in errors
    assert "key_facts must be a non-empty list" in errors


def test_validator_main_prints_usage_without_packet() -> None:
    module = _load_validator_module()
    main = cast(Callable[[], int], getattr(module, "main"))
    previous_argv = sys.argv

    try:
        sys.argv = ["validate-packet.py"]
        assert main() == 2
    finally:
        sys.argv = previous_argv


def test_validator_main_rejects_missing_packet() -> None:
    module = _load_validator_module()
    main = cast(Callable[[], int], getattr(module, "main"))
    previous_argv = sys.argv

    try:
        sys.argv = ["validate-packet.py", str(ROOT / "knowledge" / "missing.yaml")]
        assert main() == 1
    finally:
        sys.argv = previous_argv


def test_validator_main_rejects_non_mapping_packet(tmp_path: Path) -> None:
    module = _load_validator_module()
    main = cast(Callable[[], int], getattr(module, "main"))
    invalid_packet = tmp_path / "invalid.yaml"
    invalid_packet.write_text("- not-a-mapping\n", encoding="utf-8")
    previous_argv = sys.argv

    try:
        sys.argv = ["validate-packet.py", str(invalid_packet)]
        assert main() == 1
    finally:
        sys.argv = previous_argv


def test_validator_main_accepts_sample_packet() -> None:
    module = _load_validator_module()
    main = cast(Callable[[], int], getattr(module, "main"))
    previous_argv = sys.argv

    try:
        sys.argv = [
            "validate-packet.py",
            str(ROOT / "knowledge" / "basketball" / "jalen-brunson-2024-25.yaml"),
        ]
        assert main() == 0
    finally:
        sys.argv = previous_argv


def test_new_domain_scaffolds_from_template(tmp_path: Path) -> None:
    fixture_root = tmp_path / "rdw"
    (fixture_root / "scripts").mkdir(parents=True)
    (fixture_root / "domains").mkdir()
    (fixture_root / "knowledge").mkdir()
    shutil.copy2(ROOT / "scripts" / "new-domain.sh", fixture_root / "scripts" / "new-domain.sh")
    shutil.copytree(ROOT / "domains" / "_template", fixture_root / "domains" / "_template")

    subprocess.run(
        ["bash", str(fixture_root / "scripts" / "new-domain.sh"), "finance", "Finance Writing"],
        check=True,
        cwd=fixture_root,
        capture_output=True,
        text=True,
    )

    config = (fixture_root / "domains" / "finance" / "domain-config.yaml").read_text(
        encoding="utf-8"
    )
    assert "finance" in config
    assert "Finance Writing" in config
    assert (fixture_root / "knowledge" / "finance").is_dir()


def test_install_templates_keep_rdw_root_placeholder() -> None:
    template_paths = [
        ROOT / "install" / "claude-commands" / "rdw.md",
        ROOT / "install" / "claude-commands" / "rdw-batch.md",
        ROOT / "install" / "cursor-skills" / "rdw" / "SKILL.md",
        ROOT / "install" / "cursor-skills" / "rdw-batch" / "SKILL.md",
        ROOT / "install" / "codex-skills" / "research-domain-writing" / "SKILL.md",
    ]

    assert all("__RDW_ROOT__" in path.read_text(encoding="utf-8") for path in template_paths)


def test_outputs_tree_tracks_only_gitkeep_placeholders() -> None:
    tracked_outputs = [
        path for path in (ROOT / "outputs").rglob("*") if path.is_file() and path.name != ".gitkeep"
    ]

    assert tracked_outputs == []
