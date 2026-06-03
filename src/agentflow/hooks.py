"""Synchronous workflow lifecycle hook support."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime

from agentflow.exceptions import HookExecutionError
from agentflow.models import StepResult, WorkflowResult


@dataclass(slots=True)
class WorkflowStartedEvent:
    """Emitted after workflow validation and state assignment."""

    workflow_name: str
    run_id: str
    state: object
    started_at: datetime


@dataclass(slots=True)
class StepStartedEvent:
    """Emitted before a workflow step begins approval and retry handling."""

    workflow_name: str
    run_id: str
    step_name: str
    state: object
    started_at: datetime


@dataclass(slots=True)
class StepFinishedEvent:
    """Emitted after a workflow step has a final result."""

    workflow_name: str
    run_id: str
    step_name: str
    state: object
    result: StepResult


@dataclass(slots=True)
class WorkflowFinishedEvent:
    """Emitted after a workflow result has been built."""

    workflow_name: str
    run_id: str
    state: object
    result: WorkflowResult


WorkflowEvent = (
    WorkflowStartedEvent | StepStartedEvent | StepFinishedEvent | WorkflowFinishedEvent
)
WorkflowHook = Callable[[WorkflowEvent], None]


def emit_hooks(hooks: Iterable[WorkflowHook] | None, event: WorkflowEvent) -> None:
    """Emit an event to all configured hooks in order."""
    if hooks is None:
        return

    for hook in hooks:
        try:
            hook(event)
        except Exception as error:
            raise HookExecutionError(
                f"Workflow hook failed while handling {type(event).__name__}."
            ) from error


__all__ = [
    "StepFinishedEvent",
    "StepStartedEvent",
    "WorkflowEvent",
    "WorkflowFinishedEvent",
    "WorkflowHook",
    "WorkflowStartedEvent",
    "emit_hooks",
]
