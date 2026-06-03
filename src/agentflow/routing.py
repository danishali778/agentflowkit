"""Routing helpers for conditional workflow execution."""

from __future__ import annotations

from agentflow.exceptions import RouteResolutionError
from agentflow.models import (
    END,
    RouteDecision,
    StepDefinition,
    StepResult,
    StepStatus,
    WorkflowDefinition,
)


def workflow_uses_routes(workflow_definition: WorkflowDefinition) -> bool:
    """Return whether a workflow declares any route metadata."""
    return any(step.routes is not None for step in workflow_definition.steps)


def build_skipped_result(step_definition: StepDefinition, reason: str) -> StepResult:
    """Create a synthesized skipped result for a declared but unvisited step."""
    return StepResult(
        step_name=step_definition.name,
        status=StepStatus.SKIPPED,
        attempts=0,
        output=None,
        error=None,
        skipped_reason=reason,
        approval_required=step_definition.requires_approval,
    )


def finalize_step_results(
    workflow_definition: WorkflowDefinition,
    executed_results: dict[int, StepResult],
    *,
    skipped_reason: str,
) -> list[StepResult]:
    """Return declaration-ordered results, filling route-unvisited steps as skipped."""
    if not workflow_uses_routes(workflow_definition):
        return list(executed_results.values())

    results: list[StepResult] = []
    for index, step_definition in enumerate(workflow_definition.steps):
        result = executed_results.get(index)
        if result is None:
            result = build_skipped_result(step_definition, skipped_reason)
        results.append(result)
    return results


def resolve_route_decision(
    step_definition: StepDefinition,
    output: object,
    step_indexes: dict[str, int],
) -> tuple[RouteDecision, int | None]:
    """Resolve a successful step output into a route decision and next index."""
    if step_definition.routes is None:
        return RouteDecision(step_name=step_definition.name, route_key="", next_step=None), None

    if not isinstance(output, str):
        raise RouteResolutionError(
            f"Step {step_definition.name!r} returned a non-string route key."
        )

    route_target = step_definition.routes.get(output)
    if route_target is None:
        raise RouteResolutionError(
            f"Step {step_definition.name!r} returned unknown route key {output!r}."
        )

    if route_target is END:
        return (
            RouteDecision(
                step_name=step_definition.name,
                route_key=output,
                next_step=None,
                ended=True,
            ),
            None,
        )

    return (
        RouteDecision(
            step_name=step_definition.name,
            route_key=output,
            next_step=route_target,
            ended=False,
        ),
        step_indexes[route_target],
    )
