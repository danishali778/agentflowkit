"""Behavior-focused tests for the minimal workflow executor runtime."""

from agentflow.decorators import step, workflow
from agentflow.exceptions import (
    StateValidationError,
    WorkflowDefinitionError,
    WorkflowExecutionError,
)
from agentflow.models import StepStatus, WorkflowStatus


def test_decorated_workflow_can_run_and_mutate_shared_state_in_order() -> None:
    """A workflow should execute steps in declaration order and preserve shared state."""

    @workflow(name="refund_workflow")
    class RefundWorkflow:
        @step
        def check_order(self) -> str:
            self.state["events"].append("check_order")
            self.state["order_found"] = True
            return "checked"

        @step
        def verify_policy(self) -> str:
            self.state["events"].append("verify_policy")
            self.state["policy_ok"] = self.state["order_found"]
            return "verified"

    workflow_instance = RefundWorkflow()
    state = {"events": [], "order_found": False, "policy_ok": False}

    result = workflow_instance.run(state)

    assert workflow_instance.state is state
    assert result.workflow_name == "refund_workflow"
    assert result.status is WorkflowStatus.SUCCEEDED
    assert result.state is state
    assert result.state["events"] == ["check_order", "verify_policy"]
    assert result.state["order_found"] is True
    assert result.state["policy_ok"] is True
    assert [step_result.step_name for step_result in result.steps] == [
        "check_order",
        "verify_policy",
    ]
    assert [step_result.output for step_result in result.steps] == ["checked", "verified"]
    assert all(step_result.status is StepStatus.SUCCEEDED for step_result in result.steps)
    assert all(step_result.error is None for step_result in result.steps)
    assert all(step_result.attempts >= 1 for step_result in result.steps)
    assert all(step_result.finished_at >= step_result.started_at for step_result in result.steps)
    assert all(step_result.duration_ms >= 0 for step_result in result.steps)
    assert result.error is None
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.finished_at >= result.started_at
    assert result.duration_ms >= 0


def test_step_can_receive_run_context() -> None:
    """Steps with the optional context argument should receive runtime metadata."""

    @workflow
    class ContextWorkflow:
        @step
        def capture_context(self, context) -> str:
            self.state["workflow_name"] = context.workflow_name
            self.state["step_name"] = context.step_name
            self.state["run_id"] = context.run_id
            self.state["attempt"] = context.attempt
            return "captured"

    state = {"workflow_name": None, "step_name": None, "run_id": None, "attempt": None}
    result = ContextWorkflow().run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert state["workflow_name"] == "ContextWorkflow"
    assert state["step_name"] == "capture_context"
    assert isinstance(state["run_id"], str)
    assert state["run_id"]
    assert state["attempt"] == 1


def test_workflow_stops_after_first_failing_step() -> None:
    """Fail-fast behavior should preserve prior results and skip later execution."""

    @workflow
    class FailingWorkflow:
        @step
        def check_order(self) -> str:
            self.state["events"].append("check_order")
            return "checked"

        @step
        def verify_policy(self) -> None:
            self.state["events"].append("verify_policy")
            raise ValueError("policy denied")

        @step
        def generate_response(self) -> str:
            self.state["events"].append("generate_response")
            return "generated"

    state = {"events": []}
    result = FailingWorkflow().run(state)

    assert result.status is WorkflowStatus.FAILED
    assert result.error is not None
    assert isinstance(result.error, ValueError)
    assert state["events"] == ["check_order", "verify_policy"]
    assert len(result.steps) == 2
    assert result.steps[0].status is StepStatus.SUCCEEDED
    assert result.steps[0].error is None
    assert result.steps[1].status is StepStatus.FAILED
    assert result.steps[1].output is None
    assert result.steps[1].error is result.error
    assert result.steps[1].attempts >= 1
    assert result.steps[1].finished_at >= result.steps[1].started_at
    assert result.steps[1].duration_ms >= 0
    assert result.finished_at >= result.started_at
    assert result.duration_ms >= 0


def test_raise_on_failure_raises_workflow_execution_error() -> None:
    """Optional raise-on-failure mode should raise after the failing result is built."""

    @workflow
    class FailingWorkflow:
        @step
        def check_order(self) -> None:
            raise RuntimeError("upstream API down")

    try:
        FailingWorkflow().run({}, raise_on_failure=True)
    except WorkflowExecutionError as error:
        assert "FailingWorkflow" in str(error)
        assert "check_order" in str(error)
        assert "1 attempt(s)" in str(error)
        assert "RuntimeError" in str(error)
        assert isinstance(error.__cause__, RuntimeError)
    else:
        raise AssertionError("Expected WorkflowExecutionError to be raised.")


def test_raise_on_failure_after_retries_mentions_attempt_count_and_error_type() -> None:
    """Workflow boundary errors should mention retry attempts and final exception type."""

    @workflow(retries=2, retry_on=(ValueError,))
    class FailingWorkflow:
        @step
        def check_order(self) -> None:
            raise ValueError("still failing")

    try:
        FailingWorkflow().run({}, raise_on_failure=True)
    except WorkflowExecutionError as error:
        assert "FailingWorkflow" in str(error)
        assert "check_order" in str(error)
        assert "3 attempt(s)" in str(error)
        assert "ValueError" in str(error)
        assert isinstance(error.__cause__, ValueError)
    else:
        raise AssertionError("Expected WorkflowExecutionError after retry exhaustion.")


def test_workflow_definition_validation_runs_at_definition_time() -> None:
    """The @workflow decorator should validate metadata when the class is defined."""

    try:

        @workflow
        class EmptyWorkflow:
            pass
    except WorkflowDefinitionError as error:
        assert "at least one step" in str(error)
    else:
        raise AssertionError("Expected WorkflowDefinitionError for an empty workflow definition.")


def test_none_initial_state_raises_state_validation_error() -> None:
    """The runtime should reject missing initial state before executing steps."""

    @workflow
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            self.state = {}

    try:
        RefundWorkflow().run(None)
    except StateValidationError as error:
        assert "must not be None" in str(error)
    else:
        raise AssertionError("Expected StateValidationError for missing initial state.")


def test_custom_run_method_is_not_overwritten_by_workflow_decorator() -> None:
    """User-defined run methods should remain intact after decoration."""

    @workflow
    class CustomRunWorkflow:
        def run(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return ("custom", args, kwargs)

        @step
        def check_order(self) -> None:
            self.state = {}

    result = CustomRunWorkflow().run({"order_id": "ord_123"}, raise_on_failure=True)

    assert result == ("custom", ({"order_id": "ord_123"},), {"raise_on_failure": True})
