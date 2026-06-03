"""Behavior-focused tests for workflow graph export."""

from __future__ import annotations

import pytest

from agentflow import END, export_workflow_graph, step, workflow
from agentflow.exceptions import WorkflowDefinitionError


def test_linear_workflow_exports_step_nodes_and_linear_edges() -> None:
    """Linear workflows should render declaration-ordered step edges."""

    @workflow(name="refund")
    class RefundWorkflow:
        @step(description="Find the order.")
        def check_order(self) -> None:
            pass

        @step
        def approve_refund(self) -> None:
            pass

    graph = export_workflow_graph(RefundWorkflow)

    assert graph.workflow_name == "refund"
    assert [(node.id, node.label, node.kind) for node in graph.nodes] == [
        ("step_0", "check_order", "step"),
        ("step_1", "approve_refund", "step"),
    ]
    assert graph.nodes[0].description == "Find the order."
    assert [(edge.source, edge.target, edge.kind, edge.route_key) for edge in graph.edges] == [
        ("step_0", "step_1", "linear", None),
    ]


def test_export_accepts_workflow_instances() -> None:
    """Callers should be able to export from either a workflow class or instance."""

    @workflow
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            pass

    graph = export_workflow_graph(RefundWorkflow())

    assert graph.workflow_name == "RefundWorkflow"
    assert graph.nodes[0].label == "check_order"


def test_routed_workflow_exports_route_edges_without_default_linear_edge() -> None:
    """Routed steps should use their declared route map instead of linear fallback."""

    @workflow
    class RefundWorkflow:
        @step(routes={"approved": "approve_refund", "denied": "deny_refund"})
        def evaluate_refund(self) -> str:
            return "approved"

        @step
        def approve_refund(self) -> None:
            pass

        @step
        def deny_refund(self) -> None:
            pass

    graph = export_workflow_graph(RefundWorkflow)

    assert [(edge.source, edge.target, edge.kind, edge.route_key) for edge in graph.edges] == [
        ("step_0", "step_1", "route", "approved"),
        ("step_0", "step_2", "route", "denied"),
        ("step_1", "step_2", "linear", None),
    ]


def test_end_routes_create_terminal_node() -> None:
    """Routes to END should create one terminal graph node."""

    @workflow
    class ArchiveWorkflow:
        @step(routes={"done": END, "notify": "send_notification"})
        def archive_ticket(self) -> str:
            return "done"

        @step
        def send_notification(self) -> None:
            pass

    graph = export_workflow_graph(ArchiveWorkflow)

    assert [(node.id, node.label, node.kind) for node in graph.nodes] == [
        ("step_0", "archive_ticket", "step"),
        ("step_1", "send_notification", "step"),
        ("end_0", "END", "end"),
    ]
    assert [(edge.source, edge.target, edge.kind, edge.route_key) for edge in graph.edges] == [
        ("step_0", "end_0", "route", "done"),
        ("step_0", "step_1", "route", "notify"),
    ]


def test_approval_steps_are_marked_in_graph_and_mermaid() -> None:
    """Approval-gated steps should be inspectable before runtime."""

    @workflow
    class RefundWorkflow:
        @step(requires_approval=True)
        def approve_refund(self) -> None:
            pass

    graph = export_workflow_graph(RefundWorkflow)

    assert graph.nodes[0].requires_approval is True
    assert graph.to_mermaid() == "\n".join(
        [
            "flowchart TD",
            '    step_0["approve_refund\\napproval"]',
        ]
    )


def test_custom_public_step_names_are_used_as_labels_and_targets() -> None:
    """Graph labels and route targets should use public step names."""

    @workflow
    class RefundWorkflow:
        @step(name="evaluate refund", routes={"approved": "approve refund"})
        def evaluate_refund(self) -> str:
            return "approved"

        @step(name="approve refund")
        def approve_refund(self) -> None:
            pass

    graph = export_workflow_graph(RefundWorkflow)

    assert [node.label for node in graph.nodes] == ["evaluate refund", "approve refund"]
    assert graph.edges[0].target == "step_1"


def test_missing_workflow_metadata_raises_definition_error() -> None:
    """Only decorated workflow classes can be exported."""

    class PlainClass:
        pass

    with pytest.raises(WorkflowDefinitionError, match="Workflow metadata is missing"):
        export_workflow_graph(PlainClass)


def test_invalid_workflow_metadata_fails_through_existing_validation() -> None:
    """Graph export should reuse normal workflow definition validation."""

    @workflow
    class InvalidWorkflow:
        @step(routes={"again": "first"})
        def first(self) -> str:
            return "again"

    with pytest.raises(WorkflowDefinitionError, match="must point to a later step"):
        export_workflow_graph(InvalidWorkflow)


def test_mermaid_output_is_deterministic_and_uses_safe_ids() -> None:
    """Mermaid output should preserve labels while keeping stable internal node IDs."""

    @workflow(name="support")
    class SupportWorkflow:
        @step(name='triage "ticket"', routes={"needs|approval": "manager review"})
        def triage_ticket(self) -> str:
            return "needs|approval"

        @step(name="manager review", requires_approval=True, routes={"done": END})
        def manager_review(self) -> str:
            return "done"

    graph = export_workflow_graph(SupportWorkflow)

    assert graph.to_mermaid() == "\n".join(
        [
            "flowchart TD",
            '    step_0["triage \\"ticket\\""]',
            '    step_1["manager review\\napproval"]',
            "    end_0((END))",
            "    step_0 -->|needs\\|approval| step_1",
            "    step_1 -->|done| end_0",
        ]
    )
