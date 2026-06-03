"""Decorator definitions for workflow and step registration.

These decorators implement the authoring layer of the MVP by attaching metadata
to functions and classes without adding execution behavior. This keeps the API
beginner-friendly while preserving the documented separation between definition
time and runtime orchestration.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, TypeVar, overload

from agentflow.controls.hooks import WorkflowHook
from agentflow.models import (
    ApprovalDecision,
    ApprovalRequest,
    RouteTarget,
    StepDefinition,
    WorkflowDefinition,
)

STEP_DEFINITION_ATTR = "__agentflow_step_definition__"
WORKFLOW_DEFINITION_ATTR = "__agentflow_workflow_definition__"

FunctionType = TypeVar("FunctionType", bound=Callable[..., Any])
ClassType = TypeVar("ClassType", bound=type)


def _build_step_definition(
    function: FunctionType,
    *,
    name: str | None,
    retries: int | None,
    retry_on: tuple[type[BaseException], ...] | None,
    retry_delay: float | None,
    description: str | None,
    routes: dict[str, RouteTarget] | None,
    requires_approval: bool,
    approval_message: str | None,
    approval_metadata: dict[str, object] | None,
) -> StepDefinition:
    """Create step metadata for a decorated method.

    The order is assigned later by ``@workflow`` when the class body is
    inspected in declaration order.
    """
    return StepDefinition(
        name=name or function.__name__,
        method_name=function.__name__,
        order=-1,
        retries=retries,
        retry_on=retry_on,
        retry_delay=retry_delay,
        description=description,
        routes=routes,
        requires_approval=requires_approval,
        approval_message=approval_message,
        approval_metadata=approval_metadata,
    )


def _attach_step_metadata(
    function: FunctionType,
    *,
    name: str | None,
    retries: int | None,
    retry_on: tuple[type[BaseException], ...] | None,
    retry_delay: float | None,
    description: str | None,
    routes: dict[str, RouteTarget] | None,
    requires_approval: bool,
    approval_message: str | None,
    approval_metadata: dict[str, object] | None,
) -> FunctionType:
    """Attach step metadata and return the original function unchanged."""
    setattr(
        function,
        STEP_DEFINITION_ATTR,
        _build_step_definition(
            function,
            name=name,
            retries=retries,
            retry_on=retry_on,
            retry_delay=retry_delay,
            description=description,
            routes=routes,
            requires_approval=requires_approval,
            approval_message=approval_message,
            approval_metadata=approval_metadata,
        ),
    )
    return function


def _build_workflow_definition(
    cls: type,
    *,
    name: str | None,
    retries: int,
    retry_on: tuple[type[BaseException], ...],
    retry_delay: float,
) -> WorkflowDefinition:
    """Collect step metadata from a workflow class in declaration order."""
    steps: list[StepDefinition] = []

    for attribute in cls.__dict__.values():
        step_definition = getattr(attribute, STEP_DEFINITION_ATTR, None)
        if step_definition is None:
            continue

        steps.append(replace(step_definition, order=len(steps)))

    return WorkflowDefinition(
        name=name or cls.__name__,
        steps=steps,
        retries=retries,
        retry_on=retry_on,
        retry_delay=retry_delay,
    )


def _attach_workflow_metadata(
    cls: ClassType,
    *,
    name: str | None,
    retries: int,
    retry_on: tuple[type[BaseException], ...],
    retry_delay: float,
) -> ClassType:
    """Attach workflow metadata and return the original class unchanged."""
    setattr(
        cls,
        WORKFLOW_DEFINITION_ATTR,
        _build_workflow_definition(
            cls,
            name=name,
            retries=retries,
            retry_on=retry_on,
            retry_delay=retry_delay,
        ),
    )
    if "run" not in cls.__dict__:
        cls.run = _build_run_method()
    return cls


def _build_run_method() -> Callable[..., Any]:
    """Create the Phase 4 workflow run method injected by ``@workflow``."""

    def run(
        self,
        state: object,
        *,
        raise_on_failure: bool = False,
        approval_handler: Callable[[ApprovalRequest], ApprovalDecision | bool] | None = None,
        hooks: list[WorkflowHook] | tuple[WorkflowHook, ...] | None = None,
    ) -> Any:
        from agentflow.runtime import run_workflow

        return run_workflow(
            self,
            state,
            raise_on_failure=raise_on_failure,
            approval_handler=approval_handler,
            hooks=hooks,
        )

    run.__doc__ = "Run the workflow with the provided initial state."
    return run


@overload
def step(function: FunctionType, /) -> FunctionType: ...


@overload
def step(
    *,
    name: str | None = None,
    retries: int | None = None,
    retry_on: tuple[type[BaseException], ...] | None = None,
    retry_delay: float | None = None,
    description: str | None = None,
    routes: dict[str, RouteTarget] | None = None,
    requires_approval: bool = False,
    approval_message: str | None = None,
    approval_metadata: dict[str, object] | None = None,
) -> Callable[[FunctionType], FunctionType]: ...


def step(
    function: FunctionType | None = None,
    /,
    *,
    name: str | None = None,
    retries: int | None = None,
    retry_on: tuple[type[BaseException], ...] | None = None,
    retry_delay: float | None = None,
    description: str | None = None,
    routes: dict[str, RouteTarget] | None = None,
    requires_approval: bool = False,
    approval_message: str | None = None,
    approval_metadata: dict[str, object] | None = None,
) -> FunctionType | Callable[[FunctionType], FunctionType]:
    """Mark a method as a workflow step by attaching step metadata."""
    if function is not None:
        return _attach_step_metadata(
            function,
            name=name,
            retries=retries,
            retry_on=retry_on,
            retry_delay=retry_delay,
            description=description,
            routes=routes,
            requires_approval=requires_approval,
            approval_message=approval_message,
            approval_metadata=approval_metadata,
        )

    def decorator(target: FunctionType) -> FunctionType:
        return _attach_step_metadata(
            target,
            name=name,
            retries=retries,
            retry_on=retry_on,
            retry_delay=retry_delay,
            description=description,
            routes=routes,
            requires_approval=requires_approval,
            approval_message=approval_message,
            approval_metadata=approval_metadata,
        )

    return decorator


@overload
def workflow(cls: ClassType, /) -> ClassType: ...


@overload
def workflow(
    *,
    name: str | None = None,
    retries: int = 0,
    retry_on: tuple[type[BaseException], ...] = (),
    retry_delay: float = 0.0,
) -> Callable[[ClassType], ClassType]: ...


def workflow(
    cls: ClassType | None = None,
    /,
    *,
    name: str | None = None,
    retries: int = 0,
    retry_on: tuple[type[BaseException], ...] = (),
    retry_delay: float = 0.0,
) -> ClassType | Callable[[ClassType], ClassType]:
    """Mark a class as a workflow by attaching workflow definition metadata."""
    if cls is not None:
        return _attach_workflow_metadata(
            cls,
            name=name,
            retries=retries,
            retry_on=retry_on,
            retry_delay=retry_delay,
        )

    def decorator(target: ClassType) -> ClassType:
        return _attach_workflow_metadata(
            target,
            name=name,
            retries=retries,
            retry_on=retry_on,
            retry_delay=retry_delay,
        )

    return decorator
