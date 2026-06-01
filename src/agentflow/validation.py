"""Workflow definition and runtime validation helpers.

Validation is intentionally separate from decorators and execution so the MVP
can surface clear authoring errors without coupling definition-time metadata to
runtime behavior too early.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable

from agentflow.exceptions import StateValidationError, WorkflowDefinitionError
from agentflow.models import StepDefinition, WorkflowDefinition

_RESERVED_STEP_NAMES = {"run"}


def _is_exception_tuple(value: object) -> bool:
    """Return whether the provided value is a tuple of exception classes."""
    if not isinstance(value, tuple):
        return False

    return all(inspect.isclass(item) and issubclass(item, BaseException) for item in value)


def validate_step_method_signature(method: Callable[..., object]) -> None:
    """Validate that a step method matches the MVP method contract.

    Supported signatures are ``(self)`` and ``(self, context)``. Async
    functions, extra positional parameters, varargs, kwargs, and keyword-only
    parameters are rejected in Phase 3 to keep the runtime contract explicit.
    """
    if inspect.iscoroutinefunction(method):
        raise WorkflowDefinitionError("Step methods must be synchronous functions.")

    parameters = list(inspect.signature(method).parameters.values())
    if not parameters:
        raise WorkflowDefinitionError("Step methods must declare a workflow instance parameter.")

    if len(parameters) > 2:
        raise WorkflowDefinitionError(
            "Step methods may declare only the workflow instance and optional context."
        )

    for index, parameter in enumerate(parameters):
        if parameter.kind not in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            raise WorkflowDefinitionError(
                "Step methods may only use positional parameters for self and optional context."
            )

        if index == 0:
            continue


def validate_step_definition(step: StepDefinition) -> StepDefinition:
    """Validate a single step definition against the documented MVP rules."""
    if not step.name:
        raise WorkflowDefinitionError("Step definitions must have a non-empty name.")
    if step.name in _RESERVED_STEP_NAMES:
        raise WorkflowDefinitionError(f"Step name {step.name!r} is reserved.")
    if not step.method_name:
        raise WorkflowDefinitionError("Step definitions must have a non-empty method name.")
    if step.order < 0:
        raise WorkflowDefinitionError("Step definition order must be zero or greater.")
    if step.retries is not None and step.retries < 0:
        raise WorkflowDefinitionError("Step retry count must be zero or greater when provided.")
    if step.retry_on is not None and not _is_exception_tuple(step.retry_on):
        raise WorkflowDefinitionError(
            "Step retry_on must be None or a tuple of exception classes."
        )
    if step.retry_delay is not None and step.retry_delay < 0:
        raise WorkflowDefinitionError(
            "Step retry_delay must be zero or greater when provided."
        )

    return step


def validate_workflow_definition(definition: WorkflowDefinition) -> WorkflowDefinition:
    """Validate a workflow definition and all of its declared steps."""
    if not definition.steps:
        raise WorkflowDefinitionError("Workflows must define at least one step.")
    if definition.retries < 0:
        raise WorkflowDefinitionError("Workflow retry count must be zero or greater.")
    if not _is_exception_tuple(definition.retry_on):
        raise WorkflowDefinitionError(
            "Workflow retry_on must be a tuple of exception classes."
        )
    if definition.retry_delay < 0:
        raise WorkflowDefinitionError("Workflow retry_delay must be zero or greater.")

    seen_step_names: set[str] = set()
    for step in definition.steps:
        validate_step_definition(step)
        if step.name in seen_step_names:
            raise WorkflowDefinitionError(f"Duplicate step name {step.name!r} is not allowed.")
        seen_step_names.add(step.name)

    return definition


def validate_initial_state(state: object) -> object:
    """Validate the initial workflow state for the current MVP phase."""
    if state is None:
        raise StateValidationError("Initial workflow state must not be None.")

    return state
