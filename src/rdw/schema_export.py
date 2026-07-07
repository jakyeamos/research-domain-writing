from __future__ import annotations

import json
from typing import Any

SCHEMA_TARGETS = ("packet", "batch", "task-contract")
SCHEMA_FORMATS = ("jsonschema",)


def export_schema(target: str, *, format: str = "jsonschema") -> str:
    normalized_target = target.strip().lower().replace("_", "-")
    normalized_format = format.strip().lower()
    if normalized_target not in SCHEMA_TARGETS:
        raise ValueError(
            f"unknown schema target: {target} (expected one of {', '.join(SCHEMA_TARGETS)})"
        )
    if normalized_format not in SCHEMA_FORMATS:
        raise ValueError(
            f"unsupported schema format: {format} (expected one of {', '.join(SCHEMA_FORMATS)})"
        )
    builders = {
        "packet": _packet_schema,
        "batch": _batch_schema,
        "task-contract": _task_contract_schema,
    }
    return json.dumps(builders[normalized_target](), indent=2) + "\n"


def _packet_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/packet.json",
        "title": "RDW Research Packet",
        "type": "object",
        "additionalProperties": True,
        "required": [
            "id",
            "domain",
            "entity_type",
            "entity_name",
            "key_facts",
            "source_notes",
            "confidence_level",
            "last_updated",
        ],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "domain": {"type": "string", "minLength": 1},
            "entity_type": {"type": "string", "minLength": 1},
            "entity_name": {"type": "string", "minLength": 1},
            "topic": {"type": "string"},
            "confidence_level": {"type": "string", "enum": ["high", "medium", "low"]},
            "last_updated": {"type": "string", "format": "date-time"},
            "key_facts": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["id", "text"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "text": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": True,
                },
            },
            "source_notes": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["source", "accessed", "note"],
                    "properties": {
                        "source": {"type": "string", "minLength": 1},
                        "source_type": {
                            "type": "string",
                            "enum": [
                                "url",
                                "doi",
                                "book",
                                "interview",
                                "dataset",
                                "synthetic",
                                "other",
                            ],
                        },
                        "accessed": {"type": "string", "format": "date"},
                        "note": {"type": "string", "minLength": 1},
                        "fact_ids": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                        },
                    },
                    "additionalProperties": True,
                },
            },
            "extensions": {"type": "object"},
        },
    }


def _batch_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/batch.json",
        "title": "RDW Batch Task File",
        "type": "object",
        "additionalProperties": True,
        "required": ["batch_id", "tasks"],
        "properties": {
            "batch_id": {"type": "string", "minLength": 1},
            "defaults": {
                "type": "object",
                "properties": {
                    "research_depth": {
                        "type": "string",
                        "enum": ["deep", "standard", "light", "minimal", "1", "2", "3", "4"],
                    },
                    "output_format": {"type": "string"},
                },
                "additionalProperties": True,
            },
            "tasks": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["task_id", "request"],
                    "properties": {
                        "task_id": {"type": "string", "minLength": 1},
                        "request": {"type": "string", "minLength": 1},
                        "domain": {"type": "string"},
                        "entity_name": {"type": "string"},
                        "output_type": {"type": "string"},
                        "research_depth": {
                            "type": "string",
                            "enum": ["deep", "standard", "light", "minimal", "1", "2", "3", "4"],
                        },
                        "output_format": {"type": "string"},
                        "packet_id": {"type": "string"},
                    },
                    "additionalProperties": True,
                },
            },
        },
    }


def _task_contract_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/task-contract.json",
        "title": "RDW Task Contract",
        "type": "object",
        "additionalProperties": True,
        "required": [
            "task_id",
            "task",
            "domain",
            "entity_type",
            "entity_name",
            "output_type",
            "output_format",
            "audience",
            "research_depth",
            "packet_id",
        ],
        "properties": {
            "task_id": {"type": "string", "minLength": 1},
            "task": {"type": "string", "minLength": 1},
            "domain": {"type": "string", "minLength": 1},
            "pack_exists": {"type": "boolean"},
            "entity_type": {"type": "string", "minLength": 1},
            "entity_name": {"type": "string", "minLength": 1},
            "topic": {"type": "string"},
            "output_type": {"type": "string", "minLength": 1},
            "output_format": {"type": "string", "minLength": 1},
            "audience": {"type": "string", "minLength": 1},
            "research_needed": {"type": "boolean"},
            "research_depth": {
                "type": "string",
                "enum": ["deep", "standard", "light", "minimal"],
            },
            "packet_id": {"type": "string", "minLength": 1},
            "local_knowledge_paths": {
                "type": "array",
                "items": {"type": "string"},
            },
            "qa_checklist_path": {"type": "string"},
            "writing_template": {"type": "string"},
            "style_profile_path": {"type": "string"},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "inference": {"type": "object"},
        },
    }
