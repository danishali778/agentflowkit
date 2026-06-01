"""Refund workflow example for Agent Workflow Kit.

This example shows the simplest happy-path workflow: linear steps, shared
mutable state, and a final response built from prior decisions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from agentflow import step, workflow


@dataclass
class RefundState:
    """State shared across the refund workflow."""

    order_id: str
    amount: float
    order_found: bool = False
    policy_ok: bool = False
    response_text: str = ""


@workflow(name="refund_workflow")
class RefundWorkflow:
    """A small workflow that approves a refund and prepares a response."""

    @step
    def check_order(self) -> str:
        self.state.order_found = True
        return f"Order {self.state.order_id} located."

    @step
    def verify_policy(self) -> str:
        self.state.policy_ok = self.state.order_found and self.state.amount <= 100.0
        return "Refund policy check completed."

    @step
    def generate_response(self) -> str:
        if self.state.policy_ok:
            self.state.response_text = (
                f"Refund approved for order {self.state.order_id}."
            )
        else:
            self.state.response_text = (
                f"Refund denied for order {self.state.order_id}."
            )
        return self.state.response_text


def main() -> None:
    """Run the refund workflow and print a short summary."""
    workflow_instance = RefundWorkflow()
    result = workflow_instance.run(RefundState(order_id="ord_123", amount=42.50))

    print("Refund workflow result")
    print(f"Status: {result.status.value}")
    print(f"State: {asdict(result.state)}")
    print("Steps:")
    for step_result in result.steps:
        print(
            f"  - {step_result.step_name}: {step_result.status.value} "
            f"(attempts={step_result.attempts}, output={step_result.output!r})"
        )


if __name__ == "__main__":
    main()
