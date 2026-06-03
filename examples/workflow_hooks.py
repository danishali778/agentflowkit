"""Workflow lifecycle hooks example for Agent Workflow Kit.

This example shows how hooks can observe workflow execution without changing
workflow logic or final result inspection.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentflow import (
    StepFinishedEvent,
    StepStartedEvent,
    WorkflowEvent,
    WorkflowFinishedEvent,
    WorkflowStartedEvent,
    step,
    workflow,
)


@dataclass
class RefundState:
    """State shared across the refund workflow."""

    order_id: str
    approved: bool = False
    response_text: str = ""


@workflow(name="hooked_refund_workflow")
class HookedRefundWorkflow:
    """Simple workflow used to demonstrate lifecycle hooks."""

    @step
    def approve_refund(self) -> str:
        self.state.approved = True
        return "Refund approved."

    @step
    def write_response(self) -> str:
        self.state.response_text = f"Refund approved for {self.state.order_id}."
        return self.state.response_text


def log_event(event: WorkflowEvent) -> None:
    """Print a compact log line for each lifecycle event."""
    if isinstance(event, WorkflowStartedEvent):
        print(f"workflow started: {event.workflow_name}")
    elif isinstance(event, StepStartedEvent):
        print(f"step started: {event.step_name}")
    elif isinstance(event, StepFinishedEvent):
        print(
            "step finished: "
            f"{event.step_name} status={event.result.status.value} "
            f"attempts={event.result.attempts}"
        )
    elif isinstance(event, WorkflowFinishedEvent):
        print(f"workflow finished: {event.result.status.value}")


def main() -> None:
    """Run the workflow with a logging hook and print the final result."""
    state = RefundState(order_id="ord_hooked")
    result = HookedRefundWorkflow().run(state, hooks=[log_event])

    print()
    print("Final result")
    print(f"Status: {result.status.value}")
    print(f"Response: {result.state.response_text}")


if __name__ == "__main__":
    main()
