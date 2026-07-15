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
