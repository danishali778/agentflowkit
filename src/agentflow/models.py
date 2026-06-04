"""Typed runtime metadata and result models.

This module defines the shared data contracts for the MVP runtime. Keeping
these structures explicit and centralized makes later decorator, validation,
and execution phases easier to implement without drifting from the documented
architecture.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from agentflow.exceptions import ChildWorkflowExecutionError


class _EndSentinel:
    """Represents an explicit terminal route target."""

    def __repr__(self) -> str:
        return "END"


END = _EndSentinel()
RouteTarget = str | _EndSentinel


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


ChildWorkflowRunner = Callable[..., "WorkflowResult"]


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
    routes: dict[str, RouteTarget] | None = None
    requires_approval: bool = False
    approval_message: str | None = None
    approval_metadata: dict[str, object] | None = None


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
    _child_runner: ChildWorkflowRunner | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def run_child(
        self,
        workflow_instance: object,
        state: object,
        *,
        fail_parent_on_failure: bool = True,
        approval_handler: Callable[[ApprovalRequest], ApprovalDecision | bool] | None = None,
        hooks: list[Callable[[object], None]] | tuple[Callable[[object], None], ...] | None = None,
    ) -> WorkflowResult:
        """Run a child workflow synchronously from the current step context."""
        if self._child_runner is None:
            raise ChildWorkflowExecutionError(
                "Child workflows can only be run from an active workflow step context."
            )

        return self._child_runner(
            workflow_instance,
            state,
            fail_parent_on_failure=fail_parent_on_failure,
            approval_handler=approval_handler,
            hooks=hooks,
        )


@dataclass(slots=True)
class ApprovalRequest:
    """Data passed to an approval handler before an approval-gated step runs."""

    workflow_name: str
    step_name: str
    run_id: str
    state: object
    message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ApprovalDecision:
    """Decision returned by an approval handler."""

    approved: bool
    reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class RouteDecision:
    """Captures one route decision made by a workflow step."""

    step_name: str
    route_key: str
    next_step: str | None = None
    ended: bool = False


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
    route_key: str | None = None
    next_step: str | None = None
    skipped_reason: str | None = None
    approval_required: bool = False
    approval_decision: ApprovalDecision | None = None
    child_workflows: list[WorkflowResult] = field(default_factory=list)


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
    route_trace: list[RouteDecision] = field(default_factory=list)
