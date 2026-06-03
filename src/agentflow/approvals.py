"""Approval helpers for approval-gated workflow steps."""

from __future__ import annotations

from collections.abc import Callable

from agentflow.exceptions import ApprovalRequiredError
from agentflow.models import (
    ApprovalDecision,
    ApprovalRequest,
    StepDefinition,
    WorkflowDefinition,
)

ApprovalHandler = Callable[[ApprovalRequest], ApprovalDecision | bool]


def build_approval_request(
    workflow_definition: WorkflowDefinition,
    step_definition: StepDefinition,
    *,
    run_id: str,
    state: object,
) -> ApprovalRequest:
    """Create the approval payload passed to user approval handlers."""
    return ApprovalRequest(
        workflow_name=workflow_definition.name,
        step_name=step_definition.name,
        run_id=run_id,
        state=state,
        message=step_definition.approval_message,
        metadata=dict(step_definition.approval_metadata or {}),
    )


def normalize_approval_decision(decision: ApprovalDecision | bool) -> ApprovalDecision:
    """Normalize supported approval handler responses into an ApprovalDecision."""
    if isinstance(decision, ApprovalDecision):
        if not isinstance(decision.approved, bool):
            raise ApprovalRequiredError("ApprovalDecision.approved must be a boolean.")
        return decision
    if isinstance(decision, bool):
        return ApprovalDecision(approved=decision)

    raise ApprovalRequiredError(
        "Approval handlers must return an ApprovalDecision or a boolean."
    )


def request_step_approval(
    workflow_definition: WorkflowDefinition,
    step_definition: StepDefinition,
    *,
    run_id: str,
    state: object,
    approval_handler: ApprovalHandler | None,
) -> ApprovalDecision:
    """Request approval for an approval-gated step."""
    if approval_handler is None:
        raise ApprovalRequiredError(
            f"Step {step_definition.name!r} requires approval but no approval handler was provided."
        )

    approval_request = build_approval_request(
        workflow_definition,
        step_definition,
        run_id=run_id,
        state=state,
    )
    return normalize_approval_decision(approval_handler(approval_request))
