"""Behavior-focused tests for human approval callback support."""

from __future__ import annotations

import pytest

from agentflow import ApprovalDecision, ApprovalRequest, step, workflow
from agentflow.exceptions import ApprovalRequiredError, WorkflowExecutionError
from agentflow.models import StepStatus, WorkflowStatus


def test_approval_step_runs_when_handler_approves() -> None:
    """Approved steps should invoke the actual step method and record the decision."""

    @workflow
    class RefundWorkflow:
        @step(
            requires_approval=True,
            approval_message="Approve high-value refund.",
            approval_metadata={"minimum_role": "manager"},
        )
        def approve_refund(self) -> None:
            self.state["approved"] = True

    captured_requests: list[ApprovalRequest] = []

    def approve(request: ApprovalRequest) -> ApprovalDecision:
        captured_requests.append(request)
        return ApprovalDecision(
            approved=True,
            reason="Looks safe.",
            metadata={"approver": "sam"},
        )

    state = {"approved": False}
    result = RefundWorkflow().run(state, approval_handler=approve)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["approved"] is True
    assert result.steps[0].status is StepStatus.SUCCEEDED
    assert result.steps[0].attempts == 1
    assert result.steps[0].approval_required is True
    assert result.steps[0].approval_decision == ApprovalDecision(
        approved=True,
        reason="Looks safe.",
        metadata={"approver": "sam"},
    )
    assert len(captured_requests) == 1
    assert captured_requests[0].workflow_name == "RefundWorkflow"
    assert captured_requests[0].step_name == "approve_refund"
    assert captured_requests[0].state is state
    assert captured_requests[0].message == "Approve high-value refund."
    assert captured_requests[0].metadata == {"minimum_role": "manager"}


def test_approval_step_fails_when_handler_denies() -> None:
    """Denied approval should stop the workflow before invoking the step."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["called"] = True

    state = {"called": False}
    result = RefundWorkflow().run(
        state,
        approval_handler=lambda _request: ApprovalDecision(
            approved=False,
            reason="Refund amount is too high.",
        ),
    )

    assert result.status is WorkflowStatus.FAILED
    assert isinstance(result.error, ApprovalRequiredError)
    assert state["called"] is False
    assert result.steps[0].status is StepStatus.FAILED
    assert result.steps[0].attempts == 0
    assert result.steps[0].approval_required is True
    assert result.steps[0].approval_decision == ApprovalDecision(
        approved=False,
        reason="Refund amount is too high.",
    )


def test_missing_approval_handler_fails_with_approval_required_error() -> None:
    """Approval-gated steps require an approval handler."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["called"] = True

    state = {"called": False}
    result = RefundWorkflow().run(state)

    assert result.status is WorkflowStatus.FAILED
    assert isinstance(result.error, ApprovalRequiredError)
    assert state["called"] is False
    assert result.steps[0].attempts == 0


def test_bool_approval_handler_responses_are_normalized() -> None:
    """Handlers may return booleans for simple approval flows."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["approved"] = True

    state = {"approved": False}
    result = RefundWorkflow().run(state, approval_handler=lambda _request: True)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["approved"] is True
    assert result.steps[0].approval_decision == ApprovalDecision(approved=True)


def test_invalid_approval_handler_response_fails_clearly() -> None:
    """Handlers must return ApprovalDecision or bool."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["called"] = True

    result = RefundWorkflow().run(
        {"called": False},
        approval_handler=lambda _request: "approved",
    )

    assert result.status is WorkflowStatus.FAILED
    assert isinstance(result.error, ApprovalRequiredError)
    assert "ApprovalDecision or a boolean" in str(result.error)
    assert result.steps[0].attempts == 0


def test_invalid_approval_decision_state_fails_clearly() -> None:
    """ApprovalDecision.approved must be a real boolean at runtime."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["called"] = True

    result = RefundWorkflow().run(
        {"called": False},
        approval_handler=lambda _request: ApprovalDecision(approved="false"),
    )

    assert result.status is WorkflowStatus.FAILED
    assert isinstance(result.error, ApprovalRequiredError)
    assert "ApprovalDecision.approved must be a boolean" in str(result.error)
    assert result.steps[0].attempts == 0


def test_approval_handler_exception_fails_workflow() -> None:
    """Handler exceptions should fail the workflow without retrying the step."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["called"] = True

    def fail_approval(_request: ApprovalRequest) -> ApprovalDecision:
        raise RuntimeError("approval service unavailable")

    result = RefundWorkflow().run({"called": False}, approval_handler=fail_approval)

    assert result.status is WorkflowStatus.FAILED
    assert isinstance(result.error, RuntimeError)
    assert result.steps[0].attempts == 0
    assert result.steps[0].approval_decision is None


def test_raise_on_failure_wraps_approval_failures() -> None:
    """Approval failures should preserve their cause at the workflow boundary."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["called"] = True

    with pytest.raises(WorkflowExecutionError) as error_info:
        RefundWorkflow().run({"called": False}, raise_on_failure=True)

    assert "approve_refund" in str(error_info.value)
    assert isinstance(error_info.value.__cause__, ApprovalRequiredError)


def test_approved_step_still_uses_step_retries() -> None:
    """Approval should happen once before normal step retry behavior."""

    @workflow(retries=1, retry_on=(RuntimeError,))
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            self.state["calls"] += 1
            if self.state["calls"] == 1:
                raise RuntimeError("temporary processor failure")
            self.state["approved"] = True

    approvals = 0

    def approve(_request: ApprovalRequest) -> bool:
        nonlocal approvals
        approvals += 1
        return True

    state = {"calls": 0, "approved": False}
    result = RefundWorkflow().run(state, approval_handler=approve)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert approvals == 1
    assert state["calls"] == 2
    assert state["approved"] is True
    assert result.steps[0].attempts == 2


def test_approved_routed_step_still_resolves_routes() -> None:
    """Approval and branching should compose when approval succeeds."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True, routes={"approved": "approve_refund"})
        def evaluate_refund(self) -> str:
            self.state["events"].append("evaluate")
            return "approved"

        @step
        def approve_refund(self) -> None:
            self.state["events"].append("approve")

    state = {"events": []}
    result = RefundWorkflow().run(state, approval_handler=lambda _request: True)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["events"] == ["evaluate", "approve"]
    assert result.steps[0].approval_decision == ApprovalDecision(approved=True)
    assert result.steps[0].route_key == "approved"
    assert result.route_trace[0].next_step == "approve_refund"


def test_denied_approval_prevents_route_resolution() -> None:
    """Denied approval should stop before routed output is requested."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True, routes={"approved": "approve_refund"})
        def evaluate_refund(self) -> str:
            self.state["events"].append("evaluate")
            return "approved"

        @step
        def approve_refund(self) -> None:
            self.state["events"].append("approve")

    state = {"events": []}
    result = RefundWorkflow().run(state, approval_handler=lambda _request: False)

    assert result.status is WorkflowStatus.FAILED
    assert state["events"] == []
    assert result.route_trace == []
    assert result.steps[0].status is StepStatus.FAILED
    assert result.steps[1].status is StepStatus.SKIPPED
    assert result.steps[1].skipped_reason == "not reached because workflow failed"
