"""Workflow graph export helpers.

Graph export is metadata-only: it inspects workflow definitions without running
workflow steps or touching user state.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentflow.decorators import WORKFLOW_DEFINITION_ATTR
from agentflow.exceptions import WorkflowDefinitionError
from agentflow.models import END, WorkflowDefinition
from agentflow.validation.definitions import validate_workflow_definition


@dataclass(slots=True)
class WorkflowGraphNode:
    """A node in an exported workflow graph."""

    id: str
    label: str
    kind: str
    requires_approval: bool = False
    description: str | None = None


@dataclass(slots=True)
class WorkflowGraphEdge:
    """A directed edge in an exported workflow graph."""

    source: str
    target: str
    kind: str
    route_key: str | None = None


@dataclass(slots=True)
class WorkflowGraph:
    """A metadata-only graph representation of a workflow definition."""

    workflow_name: str
    nodes: list[WorkflowGraphNode]
    edges: list[WorkflowGraphEdge]

    def to_mermaid(self) -> str:
        """Render the graph as a deterministic Mermaid flowchart."""
        lines = ["flowchart TD"]

        for node in self.nodes:
            label = node.label
            if node.requires_approval:
                label = f"{label}\napproval"

            escaped_label = _escape_mermaid_text(label)
            if node.kind == "end":
                lines.append(f"    {node.id}(({escaped_label}))")
            else:
                lines.append(f"    {node.id}[\"{escaped_label}\"]")

        for edge in self.edges:
            if edge.kind == "route" and edge.route_key is not None:
                route_key = _escape_mermaid_edge_label(edge.route_key)
                lines.append(f"    {edge.source} -->|{route_key}| {edge.target}")
            else:
                lines.append(f"    {edge.source} --> {edge.target}")

        return "\n".join(lines)


def export_workflow_graph(workflow_or_class: object) -> WorkflowGraph:
    """Export workflow metadata into a graph model without executing the workflow."""
    workflow_class = (
        workflow_or_class if isinstance(workflow_or_class, type) else type(workflow_or_class)
    )
    workflow_definition = getattr(workflow_class, WORKFLOW_DEFINITION_ATTR, None)
    if workflow_definition is None:
        raise WorkflowDefinitionError("Workflow metadata is missing from the workflow class.")

    return _build_workflow_graph(validate_workflow_definition(workflow_definition))


def _build_workflow_graph(workflow_definition: WorkflowDefinition) -> WorkflowGraph:
    step_node_ids = {
        step_definition.name: f"step_{index}"
        for index, step_definition in enumerate(workflow_definition.steps)
    }
    nodes = [
        WorkflowGraphNode(
            id=step_node_ids[step_definition.name],
            label=step_definition.name,
            kind="step",
            requires_approval=step_definition.requires_approval,
            description=step_definition.description,
        )
        for step_definition in workflow_definition.steps
    ]

    uses_end = any(
        route_target is END
        for step_definition in workflow_definition.steps
        for route_target in (step_definition.routes or {}).values()
    )
    if uses_end:
        nodes.append(WorkflowGraphNode(id="end_0", label="END", kind="end"))

    edges: list[WorkflowGraphEdge] = []
    for index, step_definition in enumerate(workflow_definition.steps):
        source = step_node_ids[step_definition.name]

        if step_definition.routes is not None:
            for route_key, route_target in step_definition.routes.items():
                target = "end_0" if route_target is END else step_node_ids[route_target]
                edges.append(
                    WorkflowGraphEdge(
                        source=source,
                        target=target,
                        kind="route",
                        route_key=route_key,
                    )
                )
            continue

        if index < len(workflow_definition.steps) - 1:
            next_step = workflow_definition.steps[index + 1]
            edges.append(
                WorkflowGraphEdge(
                    source=source,
                    target=step_node_ids[next_step.name],
                    kind="linear",
                )
            )

    return WorkflowGraph(
        workflow_name=workflow_definition.name,
        nodes=nodes,
        edges=edges,
    )


def _escape_mermaid_text(value: str) -> str:
    """Escape text used inside Mermaid quoted node labels."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _escape_mermaid_edge_label(value: str) -> str:
    """Escape route labels used inside Mermaid edge label delimiters."""
    return _escape_mermaid_text(value).replace("|", "\\|")


__all__ = [
    "WorkflowGraph",
    "WorkflowGraphEdge",
    "WorkflowGraphNode",
    "export_workflow_graph",
]
