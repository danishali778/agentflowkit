"""Runtime helpers for workflow execution.

The executor owns orchestration, while this module provides the small helpers
needed to keep invocation and delegation logic readable.
"""

from __future__ import annotations

import inspect

from agentflow.executor import WorkflowExecutor
from agentflow.models import RunContext, WorkflowResult


def _invoke_step(step_method, _workflow_instance: object, context: RunContext) -> object | None:
    """Invoke a bound step method using the supported MVP signatures."""
    parameter_count = len(inspect.signature(step_method).parameters)
    if parameter_count == 0:
        return step_method()
    if parameter_count == 1:
        return step_method(context)

    raise RuntimeError("Encountered an unsupported step signature during execution.")


def run_workflow(
    workflow_instance: object,
    state: object,
    *,
    raise_on_failure: bool = False,
) -> WorkflowResult:
    """Delegate workflow execution to the MVP executor."""
    return WorkflowExecutor().run(
        workflow_instance,
        state,
        raise_on_failure=raise_on_failure,
    )
