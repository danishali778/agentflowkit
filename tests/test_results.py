"""Behavior-focused tests for the Phase 1 runtime models."""

from datetime import datetime

import agentflow
from agentflow.exceptions import (
    AgentFlowError,
    StateValidationError,
    StepExecutionError,
    WorkflowDefinitionError,
    WorkflowExecutionError,
)
from agentflow.models import (
    RunContext,
    StepDefinition,
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
)


def test_workflow_definition_defaults_match_phase_one_plan() -> None:
    """Workflow definitions should start with stable MVP defaults."""
    workflow_definition = WorkflowDefinition(name="refund_workflow")

    assert workflow_definition.name == "refund_workflow"
    assert workflow_definition.steps == []
    assert workflow_definition.retries == 0
    assert workflow_definition.retry_on == ()
    assert workflow_definition.retry_delay == 0.0


def test_step_definition_supports_defaults_and_explicit_retry_metadata() -> None:
    """Step definitions should capture both default and explicit metadata."""
    default_step = StepDefinition(name="check_order", method_name="check_order", order=0)
    configured_step = StepDefinition(
        name="verify_policy",
        method_name="verify_policy",
        order=1,
        retries=3,
        retry_on=(TimeoutError, ConnectionError),
        retry_delay=1.5,
        description="Check the refund policy before responding.",
    )

    assert default_step.retries is None
    assert default_step.retry_on is None
    assert default_step.retry_delay is None
    assert default_step.description is None

    assert configured_step.name == "verify_policy"
    assert configured_step.method_name == "verify_policy"
    assert configured_step.order == 1
    assert configured_step.retries == 3
    assert configured_step.retry_on == (TimeoutError, ConnectionError)
    assert configured_step.retry_delay == 1.5
    assert configured_step.description == "Check the refund policy before responding."


def test_run_context_stores_workflow_and_step_metadata() -> None:
    """Run context should expose identifiers needed by later executor phases."""
    context = RunContext(
        workflow_name="refund_workflow",
        run_id="run-123",
        attempt=2,
        step_name="verify_policy",
    )

    assert context.workflow_name == "refund_workflow"
    assert context.run_id == "run-123"
    assert context.attempt == 2
    assert context.step_name == "verify_policy"


def test_result_models_store_status_payloads_and_timing_fields() -> None:
    """Step and workflow results should preserve the documented execution fields."""
    started_at = datetime(2026, 1, 1, 12, 0, 0)
    finished_at = datetime(2026, 1, 1, 12, 0, 1)
    step_error = RuntimeError("temporary model failure")
    step_result = StepResult(
        step_name="generate_response",
        status=StepStatus.FAILED,
        attempts=2,
        output={"draft": "Refund approved"},
        error=step_error,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=1000,
    )
    workflow_result = WorkflowResult(
        workflow_name="refund_workflow",
        state={"approved": False},
        status=WorkflowStatus.FAILED,
        steps=[step_result],
        error=step_error,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=1000,
    )

    assert step_result.step_name == "generate_response"
    assert step_result.status is StepStatus.FAILED
    assert step_result.attempts == 2
    assert step_result.output == {"draft": "Refund approved"}
    assert step_result.error is step_error
    assert step_result.started_at == started_at
    assert step_result.finished_at == finished_at
    assert step_result.finished_at >= step_result.started_at
    assert step_result.duration_ms == 1000

    assert workflow_result.workflow_name == "refund_workflow"
    assert workflow_result.state == {"approved": False}
    assert workflow_result.status is WorkflowStatus.FAILED
    assert workflow_result.steps == [step_result]
    assert workflow_result.error is step_error
    assert workflow_result.started_at == started_at
    assert workflow_result.finished_at == finished_at
    assert workflow_result.finished_at >= workflow_result.started_at
    assert workflow_result.duration_ms == 1000


def test_status_enums_expose_documented_values() -> None:
    """Workflow and step statuses should use the documented string values."""
    assert WorkflowStatus.PENDING.value == "pending"
    assert WorkflowStatus.RUNNING.value == "running"
    assert WorkflowStatus.SUCCEEDED.value == "succeeded"
    assert WorkflowStatus.FAILED.value == "failed"
    assert WorkflowStatus.SKIPPED.value == "skipped"

    assert StepStatus.PENDING.value == "pending"
    assert StepStatus.RUNNING.value == "running"
    assert StepStatus.SUCCEEDED.value == "succeeded"
    assert StepStatus.FAILED.value == "failed"
    assert StepStatus.SKIPPED.value == "skipped"


def test_result_and_context_defaults_support_later_runtime_population() -> None:
    """Defaults should leave room for later execution phases to fill runtime data."""
    context = RunContext(workflow_name="refund_workflow", run_id="run-001")
    step_result = StepResult(step_name="check_order")
    workflow_result = WorkflowResult(workflow_name="refund_workflow", state={"order_id": "1"})

    assert context.attempt == 1
    assert context.step_name is None

    assert step_result.status is StepStatus.PENDING
    assert step_result.attempts == 0
    assert step_result.output is None
    assert step_result.error is None
    assert step_result.started_at is None
    assert step_result.finished_at is None
    assert step_result.duration_ms == 0

    assert workflow_result.status is WorkflowStatus.PENDING
    assert workflow_result.steps == []
    assert workflow_result.error is None
    assert workflow_result.started_at is None
    assert workflow_result.finished_at is None
    assert workflow_result.duration_ms == 0


def test_top_level_result_and_exception_exports_match_submodules() -> None:
    """The public package API should expose stable result and exception symbols."""
    assert agentflow.WorkflowResult is WorkflowResult
    assert agentflow.StepResult is StepResult
    assert agentflow.AgentFlowError is AgentFlowError
    assert agentflow.WorkflowDefinitionError is WorkflowDefinitionError
    assert agentflow.StepExecutionError is StepExecutionError
    assert agentflow.WorkflowExecutionError is WorkflowExecutionError
    assert agentflow.StateValidationError is StateValidationError


def test_public_api_all_contains_only_the_expected_phase_five_symbols() -> None:
    """The top-level package should expose only the intended Phase 5 names."""
    expected_exports = {
        "AgentFlowError",
        "RetryPolicy",
        "StateValidationError",
        "StepExecutionError",
        "StepResult",
        "WorkflowDefinitionError",
        "WorkflowExecutionError",
        "WorkflowResult",
        "__version__",
        "step",
        "workflow",
    }

    assert set(agentflow.__all__) == expected_exports
    assert agentflow.__version__ == "0.1.0"
    assert "WorkflowDefinition" not in agentflow.__all__
    assert "StepDefinition" not in agentflow.__all__
    assert "RunContext" not in agentflow.__all__
    assert "WorkflowStatus" not in agentflow.__all__
    assert "StepStatus" not in agentflow.__all__
