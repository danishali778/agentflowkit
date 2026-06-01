"""Typed runtime metadata and result models.

This module defines the shared data contracts for the MVP runtime. Keeping
these structures explicit and centralized makes later decorator, validation,
and execution phases easier to implement without drifting from the documented
architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class WorkflowStatus(StrEnum):
    """Represents the lifecycle state of a workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepStatus(StrEnum):
    """Represents the lifecycle state of an individual workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class StepDefinition:
    """Metadata describing a single workflow step.

    Retry configuration is stored as primitive fields in Phase 1 so later
    decorator and retry phases can evolve without introducing extra model
    indirection too early.
    """

    name: str
    method_name: str
    order: int
    retries: int | None = None
    retry_on: tuple[type[BaseException], ...] | None = None
    retry_delay: float | None = None
    description: str | None = None


@dataclass(slots=True)
class WorkflowDefinition:
    """Metadata describing a workflow class and its configured steps."""

    name: str
    steps: list[StepDefinition] = field(default_factory=list)
    retries: int = 0
    retry_on: tuple[type[BaseException], ...] = field(default_factory=tuple)
    retry_delay: float = 0.0


@dataclass(slots=True)
class RunContext:
    """Runtime metadata for a single workflow or step execution attempt."""

    workflow_name: str
    run_id: str
    attempt: int = 1
    step_name: str | None = None


@dataclass(slots=True)
class StepResult:
    """Captures the observable outcome of a single step execution."""

    step_name: str
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    output: object | None = None
    error: Exception | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0


@dataclass(slots=True)
class WorkflowResult:
    """Captures the observable outcome of a workflow execution."""

    workflow_name: str
    state: object
    status: WorkflowStatus = WorkflowStatus.PENDING
    steps: list[StepResult] = field(default_factory=list)
    error: Exception | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
