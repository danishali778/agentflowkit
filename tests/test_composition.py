"""Behavior-focused tests for synchronous workflow composition."""

from __future__ import annotations

import pytest

from agentflow import (
    END,
    ChildWorkflowExecutionError,
    RunContext,
    StepStartedEvent,
    WorkflowExecutionError,
    step,
    workflow,
)
from agentflow.models import StepStatus, WorkflowStatus


def test_parent_step_can_run_successful_child_workflow() -> None:
    """A parent step should be able to run and inspect a child workflow result."""

    @workflow
    class RefundChildWorkflow:
        @step
        def approve_refund(self) -> str:
            self.state["approved"] = True
            return "approved"

    @workflow
    class SupportParentWorkflow:
        @step
        def handle_ticket(self, context: RunContext) -> None:
            self.state["child_result"] = context.run_child(
                RefundChildWorkflow(),
                self.state["refund"],
            )

    state = {"refund": {"approved": False}}

    result = SupportParentWorkflow().run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["refund"]["approved"] is True
    assert state["child_result"].workflow_name == "RefundChildWorkflow"
    assert result.steps[0].child_workflows == [state["child_result"]]
    assert result.steps[0].child_workflows[0].status is WorkflowStatus.SUCCEEDED


def test_failed_child_workflow_fails_parent_step_by_default() -> None:
    """Child failures should stop the parent step unless the caller opts out."""

    @workflow
    class RefundChildWorkflow:
        @step
        def fail_refund(self) -> None:
            raise RuntimeError("refund service down")

    @workflow
    class SupportParentWorkflow:
        @step
        def handle_ticket(self, context: RunContext) -> None:
            context.run_child(RefundChildWorkflow(), {})

    result = SupportParentWorkflow().run({})

    assert result.status is WorkflowStatus.FAILED
    assert result.steps[0].status is StepStatus.FAILED
    assert isinstance(result.steps[0].error, ChildWorkflowExecutionError)
    assert len(result.steps[0].child_workflows) == 1
    assert result.steps[0].child_workflows[0].status is WorkflowStatus.FAILED


def test_failed_child_workflow_can_be_manually_inspected() -> None:
    """Parents may opt out of fail-fast behavior and decide how to proceed."""

    @workflow
    class RefundChildWorkflow:
        @step
        def fail_refund(self) -> None:
            raise RuntimeError("manual review required")

    @workflow
    class SupportParentWorkflow:
        @step
        def handle_ticket(self, context: RunContext) -> str:
            child_result = context.run_child(
                RefundChildWorkflow(),
                {},
                fail_parent_on_failure=False,
            )
            self.state["child_failed"] = child_result.status is WorkflowStatus.FAILED
            return "handled"

    state = {"child_failed": False}

    result = SupportParentWorkflow().run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert result.steps[0].output == "handled"
    assert state["child_failed"] is True
    assert result.steps[0].child_workflows[0].status is WorkflowStatus.FAILED


def test_child_workflow_inherits_hooks_by_default() -> None:
    """Child runs should emit hook events through inherited parent hooks."""

    @workflow
    class ChildWorkflow:
        @step
        def child_step(self) -> None:
            pass

    @workflow
    class ParentWorkflow:
        @step
        def parent_step(self, context: RunContext) -> None:
            context.run_child(ChildWorkflow(), {})

    started_steps: list[tuple[str, str]] = []

    def collect_step_starts(event: object) -> None:
        if isinstance(event, StepStartedEvent):
            started_steps.append((event.workflow_name, event.step_name))

    ParentWorkflow().run({}, hooks=[collect_step_starts])

    assert started_steps == [
        ("ParentWorkflow", "parent_step"),
        ("ChildWorkflow", "child_step"),
    ]


def test_child_workflow_inherits_approval_handler_by_default() -> None:
    """Approval-gated child steps should use the parent approval handler."""

    @workflow
    class ChildWorkflow:
        @step(requires_approval=True)
        def approved_child_step(self) -> None:
            self.state["approved"] = True

    @workflow
    class ParentWorkflow:
        @step
        def parent_step(self, context: RunContext) -> None:
            context.run_child(ChildWorkflow(), self.state["child"])

    state = {"child": {"approved": False}}

    result = ParentWorkflow().run(state, approval_handler=lambda _request: True)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["child"]["approved"] is True
    assert result.steps[0].child_workflows[0].steps[0].approval_decision.approved is True


def test_child_workflow_route_trace_is_preserved() -> None:
    """Nested routed workflows should preserve their own route trace."""

    @workflow
    class ChildWorkflow:
        @step(routes={"done": END})
        def route_to_end(self) -> str:
            return "done"

    @workflow
    class ParentWorkflow:
        @step
        def parent_step(self, context: RunContext) -> None:
            context.run_child(ChildWorkflow(), {})

    result = ParentWorkflow().run({})
    child_result = result.steps[0].child_workflows[0]

    assert child_result.status is WorkflowStatus.SUCCEEDED
    assert len(child_result.route_trace) == 1
    assert child_result.route_trace[0].route_key == "done"
    assert child_result.route_trace[0].ended is True


def test_raise_on_failure_wraps_child_workflow_failure() -> None:
    """Parent raise_on_failure should preserve child workflow failure cause."""

    @workflow
    class ChildWorkflow:
        @step
        def child_step(self) -> None:
            raise RuntimeError("boom")

    @workflow
    class ParentWorkflow:
        @step
        def parent_step(self, context: RunContext) -> None:
            context.run_child(ChildWorkflow(), {})

    with pytest.raises(WorkflowExecutionError) as error_info:
        ParentWorkflow().run({}, raise_on_failure=True)

    assert isinstance(error_info.value.__cause__, ChildWorkflowExecutionError)


def test_context_without_child_runner_fails_clearly() -> None:
    """Manually constructed contexts should not pretend they can run child workflows."""
    context = RunContext(workflow_name="ManualWorkflow", run_id="run-001")

    with pytest.raises(ChildWorkflowExecutionError):
        context.run_child(object(), {})
