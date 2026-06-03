"""Workflow execution orchestration.

The MVP executor is intentionally small: it validates the workflow definition,
assigns shared state, runs steps in order, and returns structured results. More
advanced concerns like retries are layered in later phases.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from agentflow.decorators import WORKFLOW_DEFINITION_ATTR
from agentflow.exceptions import (
    ApprovalRequiredError,
    HookExecutionError,
    RouteResolutionError,
    WorkflowDefinitionError,
    WorkflowExecutionError,
)
from agentflow.hooks import (
    StepFinishedEvent,
    StepStartedEvent,
    WorkflowFinishedEvent,
    WorkflowHook,
    WorkflowStartedEvent,
    emit_hooks,
)
from agentflow.models import (
    END,
    ApprovalDecision,
    ApprovalRequest,
    RouteDecision,
    RunContext,
    StepDefinition,
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
)
from agentflow.retry import resolve_retry_policy, should_retry, sleep_for_retry
from agentflow.validation import (
    validate_initial_state,
    validate_step_method_signature,
    validate_workflow_definition,
)


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for runtime metadata."""
    return datetime.now(timezone.utc)


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    """Return the elapsed duration between two timestamps in whole milliseconds."""
    return max(0, int((finished_at - started_at).total_seconds() * 1000))


def _workflow_uses_routes(workflow_definition: WorkflowDefinition) -> bool:
    """Return whether a workflow declares any route metadata."""
    return any(step.routes is not None for step in workflow_definition.steps)


def _build_skipped_result(step_definition: StepDefinition, reason: str) -> StepResult:
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


def _finalize_step_results(
    workflow_definition: WorkflowDefinition,
    executed_results: dict[int, StepResult],
    *,
    skipped_reason: str,
) -> list[StepResult]:
    """Return declaration-ordered results, filling route-unvisited steps as skipped."""
    if not _workflow_uses_routes(workflow_definition):
        return list(executed_results.values())

    results: list[StepResult] = []
    for index, step_definition in enumerate(workflow_definition.steps):
        result = executed_results.get(index)
        if result is None:
            result = _build_skipped_result(step_definition, skipped_reason)
        results.append(result)
    return results


def _resolve_route_decision(
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


def _build_approval_request(
    workflow_definition: WorkflowDefinition,
    step_definition: StepDefinition,
    *,
    run_id: str,
    state: object,
) -> ApprovalRequest:
    """Create the approval payload passed to user approval handlers."""
    return ApprovalRequest(
        workflow_name=workflow_definition.name,
        step_name=step_definition.name,
        run_id=run_id,
        state=state,
        message=step_definition.approval_message,
        metadata=dict(step_definition.approval_metadata or {}),
    )


def _normalize_approval_decision(decision: ApprovalDecision | bool) -> ApprovalDecision:
    """Normalize supported approval handler responses into an ApprovalDecision."""
    if isinstance(decision, ApprovalDecision):
        if not isinstance(decision.approved, bool):
            raise ApprovalRequiredError("ApprovalDecision.approved must be a boolean.")
        return decision
    if isinstance(decision, bool):
        return ApprovalDecision(approved=decision)

    raise ApprovalRequiredError(
        "Approval handlers must return an ApprovalDecision or a boolean."
    )


def _request_step_approval(
    workflow_definition: WorkflowDefinition,
    step_definition: StepDefinition,
    *,
    run_id: str,
    state: object,
    approval_handler: Callable[[ApprovalRequest], ApprovalDecision | bool] | None,
) -> ApprovalDecision:
    """Request approval for an approval-gated step."""
    if approval_handler is None:
        raise ApprovalRequiredError(
            f"Step {step_definition.name!r} requires approval but no approval handler was provided."
        )

    approval_request = _build_approval_request(
        workflow_definition,
        step_definition,
        run_id=run_id,
        state=state,
    )
    return _normalize_approval_decision(approval_handler(approval_request))


class WorkflowExecutor:
    """Execute a workflow instance using the current MVP runtime contract."""

    def run(
        self,
        workflow_instance: object,
        state: object,
        *,
        raise_on_failure: bool = False,
        approval_handler: Callable[[ApprovalRequest], ApprovalDecision | bool] | None = None,
        hooks: list[WorkflowHook] | tuple[WorkflowHook, ...] | None = None,
    ) -> WorkflowResult:
        """Run a workflow instance and return its structured execution result."""
        workflow_definition = getattr(
            type(workflow_instance),
            WORKFLOW_DEFINITION_ATTR,
            None,
        )
        if workflow_definition is None:
            raise WorkflowDefinitionError("Workflow metadata is missing from the workflow class.")

        validated_definition = validate_workflow_definition(workflow_definition)
        validated_state = validate_initial_state(state)
        workflow_instance.state = validated_state

        workflow_started_at = _utc_now()
        workflow_error: Exception | None = None
        executed_results: dict[int, StepResult] = {}
        route_trace: list[RouteDecision] = []
        run_id = uuid4().hex

        try:
            emit_hooks(
                hooks,
                WorkflowStartedEvent(
                    workflow_name=validated_definition.name,
                    run_id=run_id,
                    state=workflow_instance.state,
                    started_at=workflow_started_at,
                ),
            )
        except HookExecutionError as error:
            workflow_finished_at = _utc_now()
            workflow_result = WorkflowResult(
                workflow_name=validated_definition.name,
                state=workflow_instance.state,
                status=WorkflowStatus.FAILED,
                steps=[],
                error=error,
                started_at=workflow_started_at,
                finished_at=workflow_finished_at,
                duration_ms=_duration_ms(workflow_started_at, workflow_finished_at),
                route_trace=[],
            )
            if raise_on_failure:
                _raise_workflow_execution_error(
                    validated_definition.name,
                    workflow_error=error,
                    step_results=[],
                )
            return workflow_result

        step_indexes = {
            step_definition.name: index
            for index, step_definition in enumerate(validated_definition.steps)
        }
        current_step_index = 0
        route_ended = False

        from agentflow.runtime import _invoke_step

        def record_step_result(index: int, result: StepResult) -> HookExecutionError | None:
            """Store a step result and emit the matching lifecycle hook."""
            executed_results[index] = result
            try:
                emit_hooks(
                    hooks,
                    StepFinishedEvent(
                        workflow_name=validated_definition.name,
                        run_id=run_id,
                        step_name=result.step_name,
                        state=workflow_instance.state,
                        result=result,
                    ),
                )
            except HookExecutionError as error:
                hook_finished_at = _utc_now()
                failed_result = replace(
                    result,
                    status=StepStatus.FAILED,
                    error=error,
                    finished_at=hook_finished_at,
                    duration_ms=(
                        _duration_ms(result.started_at, hook_finished_at)
                        if result.started_at is not None
                        else result.duration_ms
                    ),
                )
                executed_results[index] = failed_result
                return error
            return None

        while current_step_index < len(validated_definition.steps):
            step_definition = validated_definition.steps[current_step_index]
            bound_method = getattr(workflow_instance, step_definition.method_name)
            unbound_method = getattr(type(workflow_instance), step_definition.method_name)
            validate_step_method_signature(unbound_method)
            retry_policy = resolve_retry_policy(validated_definition, step_definition)

            step_started_at = _utc_now()
            attempts = 0
            approval_decision: ApprovalDecision | None = None

            try:
                emit_hooks(
                    hooks,
                    StepStartedEvent(
                        workflow_name=validated_definition.name,
                        run_id=run_id,
                        step_name=step_definition.name,
                        state=workflow_instance.state,
                        started_at=step_started_at,
                    ),
                )
            except HookExecutionError as error:
                step_finished_at = _utc_now()
                executed_results[current_step_index] = StepResult(
                    step_name=step_definition.name,
                    status=StepStatus.FAILED,
                    attempts=attempts,
                    output=None,
                    error=error,
                    started_at=step_started_at,
                    finished_at=step_finished_at,
                    duration_ms=_duration_ms(step_started_at, step_finished_at),
                    approval_required=step_definition.requires_approval,
                )
                workflow_error = error
                break

            if step_definition.requires_approval:
                try:
                    approval_decision = _request_step_approval(
                        validated_definition,
                        step_definition,
                        run_id=run_id,
                        state=workflow_instance.state,
                        approval_handler=approval_handler,
                    )
                except Exception as error:
                    step_finished_at = _utc_now()
                    step_result = StepResult(
                        step_name=step_definition.name,
                        status=StepStatus.FAILED,
                        attempts=attempts,
                        output=None,
                        error=error,
                        started_at=step_started_at,
                        finished_at=step_finished_at,
                        duration_ms=_duration_ms(step_started_at, step_finished_at),
                        approval_required=True,
                    )
                    hook_error = record_step_result(current_step_index, step_result)
                    workflow_error = hook_error or error
                    break

                if not approval_decision.approved:
                    step_finished_at = _utc_now()
                    approval_error = ApprovalRequiredError(
                        f"Approval denied for step {step_definition.name!r}."
                    )
                    step_result = StepResult(
                        step_name=step_definition.name,
                        status=StepStatus.FAILED,
                        attempts=attempts,
                        output=None,
                        error=approval_error,
                        started_at=step_started_at,
                        finished_at=step_finished_at,
                        duration_ms=_duration_ms(step_started_at, step_finished_at),
                        approval_required=True,
                        approval_decision=approval_decision,
                    )
                    hook_error = record_step_result(current_step_index, step_result)
                    workflow_error = hook_error or approval_error
                    break

            while True:
                attempts += 1
                context = RunContext(
                    workflow_name=validated_definition.name,
                    step_name=step_definition.name,
                    run_id=run_id,
                    attempt=attempts,
                )

                try:
                    output = _invoke_step(bound_method, workflow_instance, context)
                except Exception as error:
                    if should_retry(retry_policy, error, attempts):
                        sleep_for_retry(retry_policy.delay)
                        continue

                    step_finished_at = _utc_now()
                    step_result = StepResult(
                        step_name=step_definition.name,
                        status=StepStatus.FAILED,
                        attempts=attempts,
                        output=None,
                        error=error,
                        started_at=step_started_at,
                        finished_at=step_finished_at,
                        duration_ms=_duration_ms(step_started_at, step_finished_at),
                        approval_required=step_definition.requires_approval,
                        approval_decision=approval_decision,
                    )
                    hook_error = record_step_result(current_step_index, step_result)
                    workflow_error = hook_error or error
                    break

                step_finished_at = _utc_now()
                try:
                    route_decision, routed_step_index = _resolve_route_decision(
                        step_definition,
                        output,
                        step_indexes,
                    )
                except RouteResolutionError as error:
                    step_result = StepResult(
                        step_name=step_definition.name,
                        status=StepStatus.FAILED,
                        attempts=attempts,
                        output=output,
                        error=error,
                        started_at=step_started_at,
                        finished_at=step_finished_at,
                        duration_ms=_duration_ms(step_started_at, step_finished_at),
                        approval_required=step_definition.requires_approval,
                        approval_decision=approval_decision,
                    )
                    hook_error = record_step_result(current_step_index, step_result)
                    workflow_error = hook_error or error
                    break

                if step_definition.routes is not None:
                    route_trace.append(route_decision)

                step_result = StepResult(
                    step_name=step_definition.name,
                    status=StepStatus.SUCCEEDED,
                    attempts=attempts,
                    output=output,
                    error=None,
                    started_at=step_started_at,
                    finished_at=step_finished_at,
                    duration_ms=_duration_ms(step_started_at, step_finished_at),
                    route_key=(
                        route_decision.route_key if step_definition.routes is not None else None
                    ),
                    next_step=(
                        route_decision.next_step if step_definition.routes is not None else None
                    ),
                    approval_required=step_definition.requires_approval,
                    approval_decision=approval_decision,
                )
                hook_error = record_step_result(current_step_index, step_result)
                if hook_error is not None:
                    workflow_error = hook_error
                    break

                if step_definition.routes is not None:
                    if route_decision.ended:
                        route_ended = True
                    else:
                        current_step_index = routed_step_index
                    break

                current_step_index += 1
                break

            if workflow_error is not None:
                break
            if route_ended:
                break

        skipped_reason = (
            "not reached because workflow ended"
            if workflow_error is None
            else "not reached because workflow failed"
        )
        step_results = _finalize_step_results(
            validated_definition,
            executed_results,
            skipped_reason=skipped_reason,
        )

        workflow_finished_at = _utc_now()
        workflow_result = WorkflowResult(
            workflow_name=validated_definition.name,
            state=workflow_instance.state,
            status=(
                WorkflowStatus.FAILED if workflow_error is not None else WorkflowStatus.SUCCEEDED
            ),
            steps=step_results,
            error=workflow_error,
            started_at=workflow_started_at,
            finished_at=workflow_finished_at,
            duration_ms=_duration_ms(workflow_started_at, workflow_finished_at),
            route_trace=route_trace,
        )

        try:
            emit_hooks(
                hooks,
                WorkflowFinishedEvent(
                    workflow_name=validated_definition.name,
                    run_id=run_id,
                    state=workflow_instance.state,
                    result=workflow_result,
                ),
            )
        except HookExecutionError as error:
            workflow_finished_at = _utc_now()
            workflow_error = error
            workflow_result.status = WorkflowStatus.FAILED
            workflow_result.error = error
            workflow_result.finished_at = workflow_finished_at
            workflow_result.duration_ms = _duration_ms(
                workflow_started_at,
                workflow_finished_at,
            )

        if workflow_error is not None and raise_on_failure:
            _raise_workflow_execution_error(
                validated_definition.name,
                workflow_error=workflow_error,
                step_results=step_results,
            )

        return workflow_result


def _raise_workflow_execution_error(
    workflow_name: str,
    *,
    workflow_error: Exception,
    step_results: list[StepResult],
) -> None:
    """Raise a workflow boundary error while preserving the original cause."""
    failing_result = next(
        (step_result for step_result in step_results if step_result.status is StepStatus.FAILED),
        None,
    )
    error_type = type(workflow_error).__name__
    if failing_result is None:
        raise WorkflowExecutionError(
            f"Workflow {workflow_name!r} failed outside step execution due to {error_type}."
        ) from workflow_error

    raise WorkflowExecutionError(
        f"Workflow {workflow_name!r} failed at step "
        f"{failing_result.step_name!r} after {failing_result.attempts} attempt(s) "
        f"due to {error_type}."
    ) from workflow_error
