"""Branching refund workflow example for Agent Workflow Kit.

This example shows conditional routing, explicit workflow termination with END,
route traces, and skipped step results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from agentflow import END, step, workflow


@dataclass
class BranchingRefundState:
    """State shared across the branching refund workflow."""

    order_id: str
    amount: float
    customer_tier: str
    refund_status: str = "pending"
    response_text: str = ""


@workflow(name="branching_refund_workflow")
class BranchingRefundWorkflow:
    """Route refund requests into approve, deny, or no-action paths."""

    @step(
        routes={
            "approved": "approve_refund",
            "denied": "deny_refund",
            "no_action": END,
        }
    )
    def evaluate_request(self) -> str:
        if self.state.amount <= 0:
            self.state.refund_status = "no_action"
            self.state.response_text = f"No refund action needed for {self.state.order_id}."
            return "no_action"
        if self.state.amount <= 100.0:
            return "approved"
        if self.state.customer_tier == "enterprise" and self.state.amount <= 250.0:
            return "approved"

        return "denied"

    @step(routes={"done": END})
    def approve_refund(self) -> str:
        self.state.refund_status = "approved"
        self.state.response_text = f"Refund approved for order {self.state.order_id}."
        return "done"

    @step(routes={"done": END})
    def deny_refund(self) -> str:
        self.state.refund_status = "denied"
        self.state.response_text = f"Refund denied for order {self.state.order_id}."
        return "done"


def run_case(state: BranchingRefundState) -> None:
    """Run one branching refund case and print a compact summary."""
    result = BranchingRefundWorkflow().run(state)

    print(f"\nCase: {state.order_id}")
    print(f"Status: {result.status.value}")
    print(f"State: {asdict(result.state)}")
    print("Route trace:")
    for decision in result.route_trace:
        next_step = decision.next_step or "END"
        print(f"  - {decision.step_name}: {decision.route_key} -> {next_step}")
    print("Steps:")
    for step_result in result.steps:
        reason = (
            f", skipped_reason={step_result.skipped_reason!r}"
            if step_result.skipped_reason
            else ""
        )
        print(
            f"  - {step_result.step_name}: {step_result.status.value} "
            f"(attempts={step_result.attempts}{reason})"
        )


def main() -> None:
    """Run approved, denied, and terminal branching examples."""
    run_case(
        BranchingRefundState(
            order_id="ord_approved",
            amount=42.50,
            customer_tier="standard",
        )
    )
    run_case(
        BranchingRefundState(
            order_id="ord_denied",
            amount=500.00,
            customer_tier="standard",
        )
    )
    run_case(
        BranchingRefundState(
            order_id="ord_no_action",
            amount=0.0,
            customer_tier="enterprise",
        )
    )


if __name__ == "__main__":
    main()
