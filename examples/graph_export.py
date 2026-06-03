"""Workflow graph export example for Agent Workflow Kit.

This example prints a Mermaid diagram from workflow metadata. It does not run
the workflow or call any approval handler.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentflow import END, export_workflow_graph, step, workflow


@dataclass
class RefundState:
    """State that would be used if this workflow were executed."""

    order_id: str
    amount: float
    approved: bool = False


@workflow(name="graph_refund_workflow")
class GraphRefundWorkflow:
    """Refund workflow used only to demonstrate graph export."""

    @step(routes={"auto_approve": END, "manager_review": "manager_review"})
    def evaluate_refund(self) -> str:
        if self.state.amount <= 50.0:
            self.state.approved = True
            return "auto_approve"
        return "manager_review"

    @step(
        requires_approval=True,
        approval_message="Manager approval required for high-value refund.",
        approval_metadata={"minimum_role": "manager"},
        routes={"approved": END},
    )
    def manager_review(self) -> str:
        self.state.approved = True
        return "approved"


def main() -> None:
    """Print the workflow graph as Mermaid text."""
    graph = export_workflow_graph(GraphRefundWorkflow)

    print("Workflow graph")
    print(f"Workflow: {graph.workflow_name}")
    print()
    print(graph.to_mermaid())


if __name__ == "__main__":
    main()
