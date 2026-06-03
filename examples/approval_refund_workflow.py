"""Human approval workflow example for Agent Workflow Kit.

This example shows a synchronous approval callback. High-value refunds ask an
external handler for a decision before the approval step mutates state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from agentflow import ApprovalDecision, ApprovalRequest, step, workflow


@dataclass
class ApprovalRefundState:
    order_id: str
    refund_amount: float
    customer_tier: str
    approved: bool = False
    denied_reason: str | None = None
    events: list[str] | None = None


@workflow(name="approval_refund_workflow")
class ApprovalRefundWorkflow:
    @step
    def prepare_request(self) -> None:
        self.state.events = ["prepared refund request"]

    @step(
        requires_approval=True,
        approval_message="High-value refund requires manager approval.",
        approval_metadata={"minimum_role": "manager"},
    )
    def approve_refund(self) -> None:
        self.state.approved = True
        self.state.events.append("refund approved")

    @step
    def summarize_result(self) -> str:
        if self.state.approved:
            return f"Refund approved for {self.state.order_id}."
        return f"Refund denied for {self.state.order_id}: {self.state.denied_reason}."


def approval_handler(request: ApprovalRequest) -> ApprovalDecision:
    state = request.state
    if state.refund_amount <= 250 or state.customer_tier == "vip":
        return ApprovalDecision(
            approved=True,
            reason="Refund is within approval policy.",
            metadata={"approver": "manager-demo"},
        )

    state.denied_reason = "Amount requires additional finance review."
    return ApprovalDecision(
        approved=False,
        reason=state.denied_reason,
        metadata={"approver": "manager-demo"},
    )


def run_case(state: ApprovalRefundState) -> None:
    result = ApprovalRefundWorkflow().run(state, approval_handler=approval_handler)

    print("\nApproval refund result")
    print(f"Status: {result.status.value}")
    print(f"State: {asdict(state)}")
    print("Step details:")
    for step_result in result.steps:
        decision = step_result.approval_decision
        decision_text = ""
        if decision is not None:
            decision_text = f", approval={decision.approved}, reason={decision.reason!r}"
        print(
            f"  - {step_result.step_name}: {step_result.status.value} "
            f"(attempts={step_result.attempts}{decision_text})"
        )


if __name__ == "__main__":
    run_case(
        ApprovalRefundState(
            order_id="ord_approved",
            refund_amount=125.0,
            customer_tier="standard",
        )
    )
    run_case(
        ApprovalRefundState(
            order_id="ord_denied",
            refund_amount=900.0,
            customer_tier="standard",
        )
    )
