"""Behavior-focused tests for retry policy resolution and execution."""

from __future__ import annotations

import agentflow
from agentflow import RetryPolicy, step, workflow
from agentflow.exceptions import WorkflowExecutionError
from agentflow.retry import resolve_retry_policy


def test_retry_policy_is_exported_from_top_level_package() -> None:
    """Phase 6 should expose RetryPolicy through the public package API."""
    from agentflow.retry import RetryPolicy as RetryPolicyFromModule

    assert agentflow.RetryPolicy is RetryPolicy
    assert agentflow.RetryPolicy is RetryPolicyFromModule


def test_step_without_retry_config_inherits_workflow_defaults() -> None:
    """Workflow-level retry settings should apply when step metadata is omitted."""

    @workflow(retries=2, retry_on=(ValueError,), retry_delay=0.25)
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            """Use workflow retry defaults."""

    step_definition = RefundWorkflow.__agentflow_workflow_definition__.steps[0]
    workflow_definition = RefundWorkflow.__agentflow_workflow_definition__
    policy = resolve_retry_policy(workflow_definition, step_definition)

    assert policy == RetryPolicy(retries=2, retry_on=(ValueError,), delay=0.25)


def test_step_with_explicit_retry_config_overrides_workflow_defaults() -> None:
    """Step-level retry settings should override workflow defaults."""

    @workflow(retries=3, retry_on=(ValueError,), retry_delay=1.0)
    class RefundWorkflow:
        @step(retries=1, retry_on=(KeyError,), retry_delay=0.5)
        def check_order(self) -> None:
            """Override workflow retry defaults."""

    step_definition = RefundWorkflow.__agentflow_workflow_definition__.steps[0]
    workflow_definition = RefundWorkflow.__agentflow_workflow_definition__
    policy = resolve_retry_policy(workflow_definition, step_definition)

    assert policy == RetryPolicy(retries=1, retry_on=(KeyError,), delay=0.5)


def test_retriable_exception_retries_and_eventually_succeeds() -> None:
    """Transient retryable failures should be retried until the step succeeds."""

    @workflow(retries=2, retry_on=(ValueError,))
    class RefundWorkflow:
        @step
        def check_order(self) -> str:
            self.state["calls"] += 1
            if self.state["calls"] < 3:
                raise ValueError("temporary issue")
            return "checked"

    state = {"calls": 0}
    result = RefundWorkflow().run(state)

    assert result.status.value == "succeeded"
    assert state["calls"] == 3
    assert len(result.steps) == 1
    assert result.steps[0].attempts == 3
    assert result.steps[0].output == "checked"
    assert result.steps[0].error is None


def test_non_retriable_exception_fails_immediately() -> None:
    """Errors outside the retry policy should not trigger extra attempts."""

    @workflow(retries=3, retry_on=(ValueError,))
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            self.state["calls"] += 1
            raise RuntimeError("permanent failure")

    state = {"calls": 0}
    result = RefundWorkflow().run(state)

    assert result.status.value == "failed"
    assert state["calls"] == 1
    assert result.steps[0].attempts == 1
    assert isinstance(result.steps[0].error, RuntimeError)


def test_retry_exhaustion_stops_workflow_and_preserves_final_error() -> None:
    """Retry exhaustion should fail the workflow and stop later steps."""

    @workflow(retries=2, retry_on=(ValueError,))
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            self.state["events"].append("check_order")
            raise ValueError("still failing")

        @step
        def verify_policy(self) -> None:
            self.state["events"].append("verify_policy")

    state = {"events": []}
    result = RefundWorkflow().run(state)

    assert result.status.value == "failed"
    assert state["events"] == ["check_order", "check_order", "check_order"]
    assert len(result.steps) == 1
    assert result.steps[0].attempts == 3
    assert isinstance(result.steps[0].error, ValueError)
    assert result.error is result.steps[0].error


def test_raise_on_failure_still_raises_after_retry_exhaustion() -> None:
    """WorkflowExecutionError should still be raised after retries are exhausted."""

    @workflow(retries=1, retry_on=(ValueError,))
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            raise ValueError("temporary issue that never recovers")

    try:
        RefundWorkflow().run({}, raise_on_failure=True)
    except WorkflowExecutionError as error:
        assert "check_order" in str(error)
        assert isinstance(error.__cause__, ValueError)
    else:
        raise AssertionError("Expected WorkflowExecutionError after retry exhaustion.")


def test_fixed_retry_delay_uses_sleep_between_attempts(monkeypatch) -> None:
    """Configured retry delay should sleep between retry attempts."""
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr("agentflow.retry.time.sleep", fake_sleep)

    @workflow(retries=2, retry_on=(ValueError,), retry_delay=0.5)
    class RefundWorkflow:
        @step
        def check_order(self) -> str:
            self.state["calls"] += 1
            if self.state["calls"] < 3:
                raise ValueError("temporary issue")
            return "checked"

    result = RefundWorkflow().run({"calls": 0})

    assert result.status.value == "succeeded"
    assert sleep_calls == [0.5, 0.5]
