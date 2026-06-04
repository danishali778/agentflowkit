"""Run one workflow from inside another workflow step."""

from __future__ import annotations

from dataclasses import dataclass

from agentflow import RunContext, step, workflow


@dataclass
class RefundState:
    order_id: str
    amount: float
    approved: bool = False
    response_text: str = ""


@workflow
class RefundWorkflow:
    @step
    def approve_small_refund(self) -> str:
        self.state.approved = self.state.amount <= 100.0
        if self.state.approved:
            self.state.response_text = f"Refund approved for {self.state.order_id}."
        else:
            self.state.response_text = f"Refund needs manual review for {self.state.order_id}."
        return self.state.response_text


@dataclass
class SupportTicketState:
    ticket_id: str
    refund: RefundState
    child_status: str = ""
    summary: str = ""


@workflow
class SupportWorkflow:
    @step
    def process_refund_request(self, context: RunContext) -> str:
        refund_result = context.run_child(
            RefundWorkflow(),
            self.state.refund,
            fail_parent_on_failure=False,
        )
        self.state.child_status = refund_result.status.value
        return f"Refund child workflow {refund_result.status.value}."

    @step
    def summarize_ticket(self) -> str:
        self.state.summary = (
            f"Ticket {self.state.ticket_id}: {self.state.refund.response_text}"
        )
        return self.state.summary


def main() -> None:
    state = SupportTicketState(
        ticket_id="ticket_456",
        refund=RefundState(order_id="ord_123", amount=49.99),
    )

    result = SupportWorkflow().run(state)

    print("Workflow composition result")
    print(f"Status: {result.status.value}")
    print(f"Child workflows on first step: {len(result.steps[0].child_workflows)}")
    print(f"Child status: {result.steps[0].child_workflows[0].status.value}")
    print(f"Summary: {result.state.summary}")


if __name__ == "__main__":
    main()
