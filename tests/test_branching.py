"""Behavior-focused tests for conditional workflow branching."""

from __future__ import annotations

import pytest

from agentflow import END, step, workflow
from agentflow.exceptions import RouteResolutionError, WorkflowExecutionError
from agentflow.models import StepStatus, WorkflowStatus


def test_routed_step_can_jump_to_later_step_and_synthesize_skipped_results() -> None:
    """A routed step should jump forward and mark unvisited branch steps as skipped."""

    @workflow
    class RefundWorkflow:
        @step(routes={"approved": "approve_refund", "denied": "deny_refund"})
        def evaluate_refund(self) -> str:
            self.state["events"].append("evaluate_refund")
            return "denied"

        @step
        def approve_refund(self) -> None:
            self.state["events"].append("approve_refund")

        @step
        def deny_refund(self) -> str:
            self.state["events"].append("deny_refund")
            return "denied"

    state = {"events": []}
    result = RefundWorkflow().run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["events"] == ["evaluate_refund", "deny_refund"]
    assert [step_result.step_name for step_result in result.steps] == [
        "evaluate_refund",
        "approve_refund",
        "deny_refund",
    ]
    assert [step_result.status for step_result in result.steps] == [
        StepStatus.SUCCEEDED,
        StepStatus.SKIPPED,
        StepStatus.SUCCEEDED,
    ]
    assert result.steps[0].route_key == "denied"
    assert result.steps[0].next_step == "deny_refund"
    assert result.steps[1].attempts == 0
    assert result.steps[1].skipped_reason == "not reached because workflow ended"
    assert len(result.route_trace) == 1
    assert result.route_trace[0].step_name == "evaluate_refund"
    assert result.route_trace[0].route_key == "denied"
    assert result.route_trace[0].next_step == "deny_refund"
    assert result.route_trace[0].ended is False


def test_routed_step_can_end_workflow_with_end_sentinel() -> None:
    """A routed step should be able to terminate successfully with END."""

    @workflow
    class ArchiveWorkflow:
        @step(routes={"done": END, "notify": "send_notification"})
        def archive_ticket(self) -> str:
            self.state["events"].append("archive_ticket")
            return "done"

        @step
        def send_notification(self) -> None:
            self.state["events"].append("send_notification")

    state = {"events": []}
    result = ArchiveWorkflow().run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["events"] == ["archive_ticket"]
    assert result.steps[0].status is StepStatus.SUCCEEDED
    assert result.steps[0].route_key == "done"
    assert result.steps[0].next_step is None
    assert result.steps[1].status is StepStatus.SKIPPED
    assert result.route_trace[0].ended is True
    assert result.route_trace[0].next_step is None


def test_route_targets_use_public_step_names() -> None:
    """Routes should target public step names, including custom names."""

    @workflow
    class RefundWorkflow:
        @step(routes={"approved": "approve_refund"})
        def evaluate_refund(self) -> str:
            return "approved"

        @step(name="approve_refund", routes={"done": END})
        def approve_refund_step(self) -> str:
            self.state["approved"] = True
            return "done"

    state = {"approved": False}
    result = RefundWorkflow().run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["approved"] is True
    assert result.route_trace[0].next_step == "approve_refund"
    assert [step_result.step_name for step_result in result.steps] == [
        "evaluate_refund",
        "approve_refund",
    ]


def test_unknown_route_key_fails_workflow() -> None:
    """Route outputs must match declared route keys."""

    @workflow
    class RefundWorkflow:
        @step(routes={"approved": "approve_refund"})
        def evaluate_refund(self) -> str:
            return "denied"

        @step
        def approve_refund(self) -> None:
            self.state["approved"] = True

    result = RefundWorkflow().run({"approved": False})

    assert result.status is WorkflowStatus.FAILED
    assert isinstance(result.error, RouteResolutionError)
    assert result.steps[0].status is StepStatus.FAILED
    assert result.steps[0].output == "denied"
    assert result.steps[1].status is StepStatus.SKIPPED
    assert result.steps[1].skipped_reason == "not reached because workflow failed"
    assert result.route_trace == []


def test_non_string_route_output_fails_workflow() -> None:
    """Routed steps must return string route keys."""

    @workflow
    class RefundWorkflow:
        @step(routes={"approved": "approve_refund"})
        def evaluate_refund(self) -> bool:
            return True

        @step
        def approve_refund(self) -> None:
            self.state["approved"] = True

    result = RefundWorkflow().run({"approved": False})

    assert result.status is WorkflowStatus.FAILED
    assert isinstance(result.error, RouteResolutionError)
    assert result.steps[0].output is True
    assert result.steps[1].status is StepStatus.SKIPPED


def test_raise_on_failure_wraps_route_resolution_error() -> None:
    """Route failures should preserve their cause at the workflow boundary."""

    @workflow
    class RefundWorkflow:
        @step(routes={"approved": "approve_refund"})
        def evaluate_refund(self) -> str:
            return "missing"

        @step
        def approve_refund(self) -> None:
            self.state["approved"] = True

    with pytest.raises(WorkflowExecutionError) as error_info:
        RefundWorkflow().run({"approved": False}, raise_on_failure=True)

    assert "evaluate_refund" in str(error_info.value)
    assert isinstance(error_info.value.__cause__, RouteResolutionError)


def test_workflow_retry_defaults_still_apply_to_routed_steps() -> None:
    """Workflow-level retries should still wrap routed step execution."""

    @workflow(retries=1, retry_on=(ValueError,))
    class RefundWorkflow:
        @step(routes={"approved": "approve_refund"})
        def evaluate_refund(self) -> str:
            self.state["calls"] += 1
            if self.state["calls"] == 1:
                raise ValueError("temporary")
            return "approved"

        @step
        def approve_refund(self) -> None:
            self.state["approved"] = True

    state = {"calls": 0, "approved": False}
    result = RefundWorkflow().run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["calls"] == 2
    assert state["approved"] is True
    assert result.steps[0].attempts == 2
    assert result.steps[0].route_key == "approved"
    assert result.route_trace[0].next_step == "approve_refund"


def test_step_retry_overrides_still_apply_to_routed_steps() -> None:
    """Step-level retries should override workflow defaults before routing."""

    @workflow(retries=0, retry_on=(ValueError,))
    class RefundWorkflow:
        @step(retries=1, retry_on=(RuntimeError,), routes={"approved": "approve_refund"})
        def evaluate_refund(self) -> str:
            self.state["calls"] += 1
            if self.state["calls"] == 1:
                raise RuntimeError("temporary")
            return "approved"

        @step
        def approve_refund(self) -> None:
            self.state["approved"] = True

    state = {"calls": 0, "approved": False}
    result = RefundWorkflow().run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["calls"] == 2
    assert state["approved"] is True
    assert result.steps[0].attempts == 2
