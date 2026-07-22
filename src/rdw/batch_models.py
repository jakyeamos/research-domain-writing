from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from rdw.yaml_io import YamlMapping, YamlValue

ExecutorTaskState = Literal[
    "queued",
    "leased",
    "running",
    "succeeded",
    "retry-wait",
    "needs-review",
    "failed",
    "cancelled",
    "reconcile-required",
    "paused",
]
BatchExecutorState = Literal[
    "idle",
    "running",
    "pause-requested",
    "paused",
    "cancel-requested",
    "cancelled",
    "completed",
    "completed-with-failures",
    "recovery-required",
]
FailurePolicy = Literal["continue", "stop"]

EXECUTOR_TASK_STATES = frozenset(
    {
        "queued",
        "leased",
        "running",
        "succeeded",
        "retry-wait",
        "needs-review",
        "failed",
        "cancelled",
        "reconcile-required",
        "paused",
    }
)
EXECUTOR_BATCH_STATES = frozenset(
    {
        "idle",
        "running",
        "pause-requested",
        "paused",
        "cancel-requested",
        "cancelled",
        "completed",
        "completed-with-failures",
        "recovery-required",
    }
)
RETRYABLE_FAILURE_CATEGORIES = frozenset({"rate_limited", "network", "provider"})
TERMINAL_EXECUTOR_TASK_STATES = frozenset({"succeeded", "cancelled", "reconcile-required"})


class BatchLeaseConflictError(ValueError):
    """Raised when another executor lease is still live."""


@dataclass(frozen=True)
class BatchExecutionPolicy:
    max_concurrency: int = 1
    max_attempts: int = 2
    retry_backoff_seconds: tuple[int, ...] = (5, 30)
    task_timeout_seconds: int = 900
    batch_timeout_seconds: int = 3600
    max_tasks: int = 100
    max_total_attempts: int = 100
    failure_policy: FailurePolicy = "continue"

    def __post_init__(self) -> None:
        if self.max_concurrency != 1:
            raise ValueError("serial batch executor requires max_concurrency: 1")
        if not 1 <= self.max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        if any(seconds < 0 for seconds in self.retry_backoff_seconds) or (
            self.max_attempts > 1 and not self.retry_backoff_seconds
        ):
            raise ValueError("retry_backoff_seconds must contain non-negative values")
        if self.task_timeout_seconds <= 0:
            raise ValueError("task_timeout_seconds must be positive")
        if self.batch_timeout_seconds <= 0:
            raise ValueError("batch_timeout_seconds must be positive")
        if not 1 <= self.max_tasks <= 100:
            raise ValueError("max_tasks must be between 1 and 100")
        if not 1 <= self.max_total_attempts <= 100:
            raise ValueError("max_total_attempts must be between 1 and 100")
        if self.failure_policy not in {"continue", "stop"}:
            raise ValueError("failure_policy must be continue or stop")

    @classmethod
    def from_mapping(cls, value: YamlValue | None) -> BatchExecutionPolicy:
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("execution policy must be a mapping")
        max_concurrency = _policy_int(value.get("max_concurrency"), "max_concurrency", 1)
        max_attempts = _policy_int(value.get("max_attempts"), "max_attempts", 2)
        retry_backoff = value.get("retry_backoff_seconds")
        if retry_backoff is None:
            backoff = (5, 30)
        elif isinstance(retry_backoff, list) and all(
            isinstance(item, int) and not isinstance(item, bool) for item in retry_backoff
        ):
            backoff = tuple(cast(int, item) for item in retry_backoff)
        else:
            raise ValueError("retry_backoff_seconds must be a list of integers")
        failure_policy_value = value.get("failure_policy", "continue")
        if failure_policy_value not in {"continue", "stop"}:
            raise ValueError("failure_policy must be continue or stop")
        return cls(
            max_concurrency=max_concurrency,
            max_attempts=max_attempts,
            retry_backoff_seconds=backoff,
            task_timeout_seconds=_policy_int(
                value.get("task_timeout_seconds"), "task_timeout_seconds", 900
            ),
            batch_timeout_seconds=_policy_int(
                value.get("batch_timeout_seconds"), "batch_timeout_seconds", 3600
            ),
            max_tasks=_policy_int(value.get("max_tasks"), "max_tasks", 100),
            max_total_attempts=_policy_int(
                value.get("max_total_attempts"), "max_total_attempts", 100
            ),
            failure_policy=cast(FailurePolicy, failure_policy_value),
        )

    def as_dict(self) -> YamlMapping:
        return {
            "max_concurrency": self.max_concurrency,
            "max_attempts": self.max_attempts,
            "retry_backoff_seconds": list(self.retry_backoff_seconds),
            "task_timeout_seconds": self.task_timeout_seconds,
            "batch_timeout_seconds": self.batch_timeout_seconds,
            "max_tasks": self.max_tasks,
            "max_total_attempts": self.max_total_attempts,
            "failure_policy": self.failure_policy,
        }


@dataclass(frozen=True)
class FixtureBatchPlan:
    batch_id: str
    fixtures: dict[str, Path]
    policy: BatchExecutionPolicy


@dataclass(frozen=True)
class BatchTaskProjection:
    task_id: str
    state: ExecutorTaskState
    attempts: int = 0
    attempt_id: str | None = None
    last_error: str | None = None
    receipt_path: str | None = None
    next_retry_at: str | None = None
    retryable: bool = False
    failure_category: str | None = None
    adapter_status: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "state": self.state,
            "attempts": self.attempts,
            "attempt_id": self.attempt_id,
            "last_error": self.last_error,
            "receipt_path": self.receipt_path,
            "next_retry_at": self.next_retry_at,
            "retryable": self.retryable,
            "failure_category": self.failure_category,
            "adapter_status": self.adapter_status,
        }


@dataclass(frozen=True)
class BatchEventProjection:
    batch_state: BatchExecutorState
    tasks: dict[str, BatchTaskProjection]
    applied_event_ids: tuple[str, ...]
    duplicate_event_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "batch_state": self.batch_state,
            "tasks": {task_id: task.as_dict() for task_id, task in self.tasks.items()},
            "applied_event_ids": list(self.applied_event_ids),
            "duplicate_event_ids": list(self.duplicate_event_ids),
        }


@dataclass(frozen=True)
class BatchExecutionResult:
    batch_id: str
    state: BatchExecutorState
    task_count: int
    completed: int
    needs_review: int
    failed: int
    cancelled: int
    total_attempts: int
    tasks: tuple[BatchTaskProjection, ...]
    dry_run: bool = False
    recovery_required: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "batch_id": self.batch_id,
            "state": self.state,
            "task_count": self.task_count,
            "completed": self.completed,
            "needs_review": self.needs_review,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "total_attempts": self.total_attempts,
            "tasks": [task.as_dict() for task in self.tasks],
            "dry_run": self.dry_run,
            "recovery_required": self.recovery_required,
        }


@dataclass(frozen=True)
class BatchLease:
    lease_id: str
    batch_id: str
    acquired_at: str
    expires_at: str


def _policy_int(value: YamlValue | None, key: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value
