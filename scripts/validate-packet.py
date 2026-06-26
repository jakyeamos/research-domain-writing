#!/usr/bin/env python3
"""Minimal YAML research packet validator."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED = {
    "id",
    "domain",
    "entity_type",
    "entity_name",
    "key_facts",
    "source_notes",
    "confidence_level",
    "last_updated",
}


def validate(data: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED:
        if field not in data or data[field] in (None, "", []):
            errors.append(f"missing or empty required field: {field}")
    if data.get("confidence_level") not in {"high", "medium", "low"}:
        errors.append("confidence_level must be high|medium|low")
    key_facts = data.get("key_facts")
    if not isinstance(key_facts, list) or len(key_facts) < 1:
        errors.append("key_facts must be a non-empty list")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate-packet.py <packet.yaml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        print("invalid: root must be a mapping", file=sys.stderr)
        return 1
    errors = validate(data)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
