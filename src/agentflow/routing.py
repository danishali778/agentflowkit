"""Compatibility wrapper for routing controls."""

from agentflow.controls.routing import (
    build_skipped_result,
    finalize_step_results,
    resolve_route_decision,
    workflow_uses_routes,
)

__all__ = [
    "build_skipped_result",
    "finalize_step_results",
    "resolve_route_decision",
    "workflow_uses_routes",
]
