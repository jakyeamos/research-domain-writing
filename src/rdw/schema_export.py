from __future__ import annotations

import json

from rdw.contracts import (
    BATCH_REQUIRED_FIELDS,
    DIFF_BASELINE_REQUIRED_FIELDS,
    DIFF_QA_REQUIRED_FIELDS,
    DRAFT_CLAIM_LEDGER_REQUIRED_FIELDS,
    PACKET_REQUIRED_FIELDS,
    TASK_CONTRACT_REQUIRED_FIELDS,
)

SCHEMA_TARGETS = (
    "packet",
    "batch",
    "task-contract",
    "artifact-request",
    "artifact-receipt",
    "diff-baseline",
    "draft-claim-ledger",
    "diff-qa",
)
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
        "artifact-request": _artifact_request_schema,
        "artifact-receipt": _artifact_receipt_schema,
        "diff-baseline": _diff_baseline_schema,
        "draft-claim-ledger": _draft_claim_ledger_schema,
        "diff-qa": _diff_qa_schema,
    }
    return json.dumps(builders[normalized_target](), indent=2) + "\n"


def _packet_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/packet.json",
        "title": "RDW Research Packet",
        "type": "object",
        "additionalProperties": True,
        "required": list(PACKET_REQUIRED_FIELDS),
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


def _batch_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/batch.json",
        "title": "RDW Batch Task File",
        "type": "object",
        "additionalProperties": True,
        "required": list(BATCH_REQUIRED_FIELDS),
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


def _task_contract_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/task-contract.json",
        "title": "RDW Task Contract",
        "type": "object",
        "additionalProperties": True,
        "required": list(TASK_CONTRACT_REQUIRED_FIELDS),
        "properties": {
            "task_id": {"type": "string", "minLength": 1},
            "task": {"type": "string", "minLength": 1},
            "domain": {"type": "string", "minLength": 1},
            "pack_exists": {"type": "boolean"},
            "entity_type": {"type": "string", "minLength": 1},
            "entity_name": {"type": "string", "minLength": 1},
            "topic": {"type": "string"},
            "output_type": {"type": "string", "minLength": 1},
            "artifact_type": {"type": "string", "minLength": 1},
            "channel": {"type": "string", "minLength": 1},
            "intent": {"type": "string", "minLength": 1},
            "output_format": {"type": "string", "minLength": 1},
            "audience": {"type": "string", "minLength": 1},
            "research_needed": {"type": "boolean"},
            "research_depth": {
                "type": "string",
                "enum": ["deep", "standard", "light", "minimal"],
            },
            "execution_lane": {
                "type": "string",
                "enum": ["full", "lightweight"],
            },
            "packet_id": {"type": "string", "minLength": 1},
            "research_card_path": {"type": "string"},
            "local_knowledge_paths": {
                "type": "array",
                "items": {"type": "string"},
            },
            "qa_checklist_path": {"type": "string"},
            "writing_template": {"type": "string"},
            "style_profile_path": {"type": "string"},
            "artifact_profile_path": {"type": "string"},
            "diff_qa_required": {"type": "boolean"},
            "diff_qa_mode": {"enum": ["packet", "draft"]},
            "diff_qa_baseline_path": {"type": "string"},
            "diff_qa_path": {"type": "string"},
            "human_approval_required": {"type": "boolean"},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "inference": {"type": "object"},
        },
    }


def _artifact_request_schema() -> dict[str, object]:
    evidence_item = {
        "type": "object",
        "additionalProperties": True,
        "required": ["id", "kind", "text", "source"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "kind": {"type": "string", "minLength": 1},
            "text": {"type": "string", "minLength": 1},
            "source": {"type": "string", "minLength": 1},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/artifact-request.json",
        "title": "RDW Writing Artifact Request",
        "type": "object",
        "additionalProperties": True,
        "required": [
            "schema_version",
            "artifact_id",
            "artifact_type",
            "channel",
            "intent",
            "content",
            "evidence",
            "claim_bindings",
            "constraints",
        ],
        "properties": {
            "schema_version": {"const": "rdw-artifact-request/v1"},
            "artifact_id": {"type": "string", "minLength": 1},
            "artifact_type": {"type": "string", "minLength": 1},
            "channel": {"type": "string", "minLength": 1},
            "intent": {"type": "string", "minLength": 1},
            "audience": {"type": "object"},
            "content": {
                "type": "object",
                "required": ["body"],
                "properties": {
                    "subject": {"type": "string"},
                    "body": {"type": "string", "minLength": 1},
                },
                "additionalProperties": True,
            },
            "evidence": {"type": "array", "items": evidence_item},
            "claim_bindings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["claim", "evidence_ids"],
                    "properties": {
                        "claim": {"type": "string", "minLength": 1},
                        "evidence_ids": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "minLength": 1},
                        },
                    },
                    "additionalProperties": True,
                },
            },
            "constraints": {
                "type": "object",
                "required": ["human_approval_required"],
                "properties": {"human_approval_required": {"const": True}},
                "additionalProperties": True,
            },
        },
    }


def _artifact_receipt_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/artifact-receipt.json",
        "title": "RDW Writing Artifact Quality Receipt",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "policy_version",
            "artifact_id",
            "artifact_type",
            "channel",
            "request_hash",
            "contract_hash",
            "artifact_hash",
            "ok",
            "status",
            "human_approval_required",
            "checks",
            "reasons",
        ],
        "properties": {
            "schema_version": {"const": "rdw-artifact-receipt/v1"},
            "policy_version": {"type": "integer", "minimum": 1},
            "artifact_id": {"type": "string"},
            "artifact_type": {"type": "string"},
            "channel": {"type": "string"},
            "request_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "contract_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "artifact_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "ok": {"type": "boolean"},
            "status": {"enum": ["approved_for_human_review", "blocked"]},
            "human_approval_required": {"const": True},
            "checks": {"type": "array"},
            "reasons": {"type": "array", "items": {"type": "string"}},
        },
    }


def _diff_baseline_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/diff-baseline.json",
        "title": "RDW Approved Diff-QA Baseline",
        "type": "object",
        "additionalProperties": True,
        "required": list(DIFF_BASELINE_REQUIRED_FIELDS),
        "properties": {
            "schema_version": {"const": 1},
            "kind": {"const": "diff_baseline"},
            "baseline_id": {"type": "string", "minLength": 1},
            "artifact_kind": {"enum": ["packet", "draft"]},
            "artifact_path": {"type": "string", "minLength": 1},
            "content_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "packet_id": {"type": "string", "minLength": 1},
            "packet_revision_id": {"type": "string", "minLength": 1},
            "claim_ledger_path": {"type": "string", "minLength": 1},
            "qa_status": {"const": "pass"},
            "approved": {"const": True},
            "approved_by": {"const": "human"},
            "approved_at": {"type": "string", "format": "date-time"},
        },
    }


def _draft_claim_ledger_schema() -> dict[str, object]:
    claim = {
        "type": "object",
        "additionalProperties": True,
        "required": ["claim_id", "text", "fact_ids", "source_ids"],
        "properties": {
            "claim_id": {"type": "string", "minLength": 1},
            "text": {"type": "string", "minLength": 1},
            "fact_ids": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "source_ids": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "uncertainty": {"type": "string"},
            "required": {"type": "boolean"},
        },
    }
    rule = {
        "type": "object",
        "additionalProperties": True,
        "required": ["rule_id", "status"],
        "properties": {
            "rule_id": {"type": "string", "minLength": 1},
            "status": {"enum": ["pass", "fail", "unknown"]},
            "evidence": {"type": "string"},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/draft-claim-ledger.json",
        "title": "RDW Draft Claim Ledger",
        "type": "object",
        "additionalProperties": True,
        "required": list(DRAFT_CLAIM_LEDGER_REQUIRED_FIELDS),
        "properties": {
            "schema_version": {"const": 1},
            "kind": {"const": "draft_claim_ledger"},
            "output_id": {"type": "string", "minLength": 1},
            "draft_path": {"type": "string", "minLength": 1},
            "claims": {"type": "array", "items": claim},
            "rules": {"type": "array", "items": rule},
        },
    }


def _diff_qa_schema() -> dict[str, object]:
    issue = {
        "type": "object",
        "additionalProperties": True,
        "required": ["id", "code", "severity", "category", "subject_type", "description"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "code": {"pattern": "^DQA-00[1-9]$|^DQA-010$"},
            "severity": {"enum": ["blocker", "major", "minor"]},
            "category": {"type": "string", "minLength": 1},
            "subject_type": {"type": "string", "minLength": 1},
            "subject_id": {"type": ["string", "null"]},
            "description": {"type": "string", "minLength": 1},
            "suggested_fix": {"type": "string"},
        },
    }
    counts = {
        "type": "object",
        "required": [
            "claims_added",
            "claims_removed",
            "claims_changed",
            "source_links_removed",
            "uncertainty_removed",
            "rules_regressed",
        ],
        "properties": {
            field: {"type": "integer", "minimum": 0}
            for field in (
                "claims_added",
                "claims_removed",
                "claims_changed",
                "source_links_removed",
                "uncertainty_removed",
                "rules_regressed",
            )
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rdw.dev/schemas/diff-qa.json",
        "title": "RDW Evidence-aware Diff QA Report",
        "type": "object",
        "additionalProperties": True,
        "required": list(DIFF_QA_REQUIRED_FIELDS),
        "properties": {
            "schema_version": {"const": 1},
            "kind": {"const": "diff_qa"},
            "output_id": {"type": "string", "minLength": 1},
            "comparison": {"type": "object"},
            "summary": {
                "type": "object",
                "required": [
                    "status",
                    "pass",
                    "needs_human_review",
                    "blocking_issue_count",
                    "major_issue_count",
                    "minor_issue_count",
                    "counts",
                ],
                "properties": {
                    "status": {"enum": ["pass", "fail", "indeterminate"]},
                    "pass": {"type": "boolean"},
                    "needs_human_review": {"type": "boolean"},
                    "blocking_issue_count": {"type": "integer", "minimum": 0},
                    "major_issue_count": {"type": "integer", "minimum": 0},
                    "minor_issue_count": {"type": "integer", "minimum": 0},
                    "counts": counts,
                },
            },
            "issues": {"type": "array", "items": issue},
        },
    }
