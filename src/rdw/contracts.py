from __future__ import annotations

PACKET_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "domain",
    "entity_type",
    "entity_name",
    "key_facts",
    "source_notes",
    "confidence_level",
    "last_updated",
)

BATCH_REQUIRED_FIELDS: tuple[str, ...] = ("batch_id", "tasks")

TASK_CONTRACT_REQUIRED_FIELDS: tuple[str, ...] = (
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
)

DIFF_BASELINE_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "baseline_id",
    "artifact_kind",
    "artifact_path",
    "content_sha256",
    "qa_status",
    "approved",
    "approved_by",
    "approved_at",
)

DRAFT_CLAIM_LEDGER_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "output_id",
    "draft_path",
    "claims",
)

DIFF_QA_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "output_id",
    "comparison",
    "summary",
    "issues",
)
