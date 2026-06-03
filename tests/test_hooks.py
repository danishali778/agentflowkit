"""Behavior-focused tests for workflow lifecycle hooks."""

from __future__ import annotations

import pytest

from agentflow import (
    END,
    HookExecutionError,
    StepFinishedEvent,
    StepStartedEvent,
    WorkflowFinishedEvent,
    WorkflowStartedEvent,
    step,
    workflow,
)
from agentflow.exceptions import ApprovalRequiredError, WorkflowExecutionError
from agentflow.models import StepStatus, WorkflowStatus


def test_hooks_receive_workflow_started_and_finished_events() -> None:
    """Successful workflows should emit workflow boundary events."""

    @workflow
    class RefundWorkflow:
        @step
        def approve_refund(self) -> str:
            return "approved"

    events: list[object] = []

    result = RefundWorkflow().run({}, hooks=[events.append])

    assert result.status is WorkflowStatus.SUCCEEDED
    assert isinstance(events[0], WorkflowStartedEvent)
    assert isinstance(events[-1], WorkflowFinishedEvent)
    assert events[0].workflow_name == "RefundWorkflow"
    assert events[-1].result is result
    assert events[0].run_id == events[-1].run_id


def test_hooks_receive_step_events_in_declaration_order() -> None:
    """Step hooks should be emitted in declaration order."""

    @workflow
    class RefundWorkflow:
        @step
        def check_order(self) -> str:
            return "checked"

        @step
        def approve_refund(self) -> str:
            return "approved"

    events: list[object] = []

    RefundWorkflow().run({}, hooks=[events.append])

    step_events = [
        (type(event).__name__, event.step_name)
        for event in events
        if isinstance(event, StepStartedEvent | StepFinishedEvent)
    ]
    assert step_events == [
        ("StepStartedEvent", "check_order"),
        ("StepFinishedEvent", "check_order"),
        ("StepStartedEvent", "approve_refund"),
        ("StepFinishedEvent", "approve_refund"),
    ]


def test_step_finished_event_contains_final_step_result() -> None:
    """Step finished events should expose output and attempts."""

    @workflow(retries=1, retry_on=(RuntimeError,))
    class RefundWorkflow:
        @step
        def approve_refund(self) -> str:
            self.state["calls"] += 1
            if self.state["calls"] == 1:
                raise RuntimeError("temporary")
            return "approved"

    step_results = []

    def collect_finished(event: object) -> None:
        if isinstance(event, StepFinishedEvent):
            step_results.append(event.result)

    result = RefundWorkflow().run({"calls": 0}, hooks=[collect_finished])

    assert result.status is WorkflowStatus.SUCCEEDED
    assert len(step_results) == 1
    assert step_results[0].output == "approved"
    assert step_results[0].attempts == 2


def test_routed_workflows_emit_events_only_for_visited_steps() -> None:
    """Skipped branch steps should not receive start or finish hook events."""

    @workflow
    class RefundWorkflow:
        @step(routes={"approved": "approve_refund", "denied": "deny_refund"})
        def evaluate_refund(self) -> str:
            return "denied"

        @step
        def approve_refund(self) -> None:
            pass

        @step(routes={"done": END})
        def deny_refund(self) -> str:
            return "done"

    events: list[object] = []
    result = RefundWorkflow().run({}, hooks=[events.append])

    visited_step_names = [
        event.step_name
        for event in events
        if isinstance(event, StepStartedEvent | StepFinishedEvent)
    ]
    assert result.steps[1].status is StepStatus.SKIPPED
    assert visited_step_names == [
        "evaluate_refund",
        "evaluate_refund",
        "deny_refund",
        "deny_refund",
    ]


def test_approval_success_and_denial_emit_step_finished_events() -> None:
    """Approval outcomes should still be visible through step finished hooks."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["approved"] = True

    approved_events: list[StepFinishedEvent] = []

    def collect_approved(event: object) -> None:
        if isinstance(event, StepFinishedEvent):
            approved_events.append(event)

    approved_state = {"approved": False}
    approved_result = RefundWorkflow().run(
        approved_state,
        approval_handler=lambda _request: True,
        hooks=[collect_approved],
    )

    denied_events: list[object] = []
    denied_result = RefundWorkflow().run(
        {"approved": False},
        approval_handler=lambda _request: False,
        hooks=[denied_events.append],
    )

    assert approved_result.status is WorkflowStatus.SUCCEEDED
    assert approved_state["approved"] is True
    assert approved_events[0].result.approval_decision.approved is True
    assert denied_result.status is WorkflowStatus.FAILED
    assert isinstance(denied_result.error, ApprovalRequiredError)
    assert any(
        isinstance(event, StepFinishedEvent)
        and event.result.status is StepStatus.FAILED
        and event.result.approval_decision.approved is False
        for event in denied_events
    )
    assert isinstance(denied_events[-1], WorkflowFinishedEvent)
    assert denied_events[-1].result.status is WorkflowStatus.FAILED


def test_callable_classes_and_multiple_hooks_are_supported() -> None:
    """Hooks may be callable objects and should run in caller-provided order."""

    @workflow
    class RefundWorkflow:
        @step
        def approve_refund(self) -> str:
            return "approved"

    calls: list[str] = []

    class Recorder:
        def __init__(self, label: str) -> None:
            self.label = label

        def __call__(self, event: object) -> None:
            calls.append(f"{self.label}:{type(event).__name__}")

    RefundWorkflow().run({}, hooks=[Recorder("first"), Recorder("second")])

    assert calls[:2] == [
        "first:WorkflowStartedEvent",
        "second:WorkflowStartedEvent",
    ]


def test_hook_return_values_are_ignored() -> None:
    """Hook callbacks should observe events without influencing success by return value."""

    @workflow
    class RefundWorkflow:
        @step
        def approve_refund(self) -> str:
            return "approved"

    def returning_hook(_event: object) -> str:
        return "ignored"

    result = RefundWorkflow().run({}, hooks=[returning_hook])

    assert result.status is WorkflowStatus.SUCCEEDED


def test_hook_exception_fails_workflow_with_hook_execution_error() -> None:
    """Hook exceptions should become framework-specific workflow failures."""

    @workflow
    class RefundWorkflow:
        @step
        def approve_refund(self) -> str:
            return "approved"

    def fail_on_step_start(event: object) -> None:
        if isinstance(event, StepStartedEvent):
            raise RuntimeError("logging backend down")

    result = RefundWorkflow().run({}, hooks=[fail_on_step_start])

    assert result.status is WorkflowStatus.FAILED
    assert isinstance(result.error, HookExecutionError)
    assert isinstance(result.error.__cause__, RuntimeError)
    assert result.steps[0].status is StepStatus.FAILED
    assert result.steps[0].attempts == 0
    assert isinstance(result.steps[0].error, HookExecutionError)


def test_raise_on_failure_wraps_hook_failures() -> None:
    """Hook failures should preserve their cause at the workflow boundary."""

    @workflow
    class RefundWorkflow:
        @step
        def approve_refund(self) -> str:
            return "approved"

    def fail_on_workflow_start(_event: object) -> None:
        raise RuntimeError("metrics service down")

    with pytest.raises(WorkflowExecutionError) as error_info:
        RefundWorkflow().run({}, hooks=[fail_on_workflow_start], raise_on_failure=True)

    assert isinstance(error_info.value.__cause__, HookExecutionError)
    assert isinstance(error_info.value.__cause__.__cause__, RuntimeError)
