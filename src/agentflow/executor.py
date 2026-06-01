"""Workflow execution orchestration.

The MVP executor is intentionally small: it validates the workflow definition,
assigns shared state, runs steps in order, and returns structured results. More
advanced concerns like retries are layered in later phases.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agentflow.decorators import WORKFLOW_DEFINITION_ATTR
from agentflow.exceptions import WorkflowDefinitionError, WorkflowExecutionError
from agentflow.models import RunContext, StepResult, StepStatus, WorkflowResult, WorkflowStatus
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


class WorkflowExecutor:
    """Execute a workflow instance using the current MVP runtime contract."""

    def run(
        self,
        workflow_instance: object,
        state: object,
        *,
        raise_on_failure: bool = False,
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
        step_results: list[StepResult] = []
        run_id = uuid4().hex

        from agentflow.runtime import _invoke_step

        for step_definition in validated_definition.steps:
            bound_method = getattr(workflow_instance, step_definition.method_name)
            unbound_method = getattr(type(workflow_instance), step_definition.method_name)
            validate_step_method_signature(unbound_method)
            retry_policy = resolve_retry_policy(validated_definition, step_definition)

            step_started_at = _utc_now()
            attempts = 0

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
                    step_results.append(
                        StepResult(
                            step_name=step_definition.name,
                            status=StepStatus.FAILED,
                            attempts=attempts,
                            output=None,
                            error=error,
                            started_at=step_started_at,
                            finished_at=step_finished_at,
                            duration_ms=_duration_ms(step_started_at, step_finished_at),
                        )
                    )
                    workflow_error = error
                    break

                step_finished_at = _utc_now()
                step_results.append(
                    StepResult(
                        step_name=step_definition.name,
                        status=StepStatus.SUCCEEDED,
                        attempts=attempts,
                        output=output,
                        error=None,
                        started_at=step_started_at,
                        finished_at=step_finished_at,
                        duration_ms=_duration_ms(step_started_at, step_finished_at),
                    )
                )
                break

            if workflow_error is not None:
                break

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
        )

        if workflow_error is not None and raise_on_failure:
            failing_result = step_results[-1]
            failing_step = failing_result.step_name
            error_type = type(workflow_error).__name__
            raise WorkflowExecutionError(
                f"Workflow {validated_definition.name!r} failed at step "
                f"{failing_step!r} after {failing_result.attempts} attempt(s) "
                f"due to {error_type}."
            ) from workflow_error

        return workflow_result
