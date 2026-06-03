"""Behavior-focused tests for decorator metadata registration."""

import agentflow
from agentflow.decorators import step, workflow
from agentflow.models import WorkflowDefinition

STEP_DEFINITION_ATTR = "__agentflow_step_definition__"
WORKFLOW_DEFINITION_ATTR = "__agentflow_workflow_definition__"


def test_step_bare_form_attaches_metadata_without_wrapping_function() -> None:
    """Bare step decoration should preserve the original function object."""

    def check_order(self) -> str:
        """Check whether the order exists."""
        return "checked"

    decorated = step(check_order)
    step_definition = getattr(decorated, STEP_DEFINITION_ATTR)

    assert decorated is check_order
    assert decorated.__doc__ == "Check whether the order exists."
    assert step_definition.name == "check_order"
    assert step_definition.method_name == "check_order"
    assert step_definition.retries is None
    assert step_definition.retry_on is None
    assert step_definition.retry_delay is None
    assert step_definition.description is None


def test_step_configured_form_captures_explicit_metadata() -> None:
    """Configured step decoration should store the provided metadata values."""

    @step(
        name="policy_check",
        retries=3,
        retry_on=(TimeoutError, ConnectionError),
        retry_delay=1.5,
        description="Check whether the refund policy allows approval.",
        routes={"approved": "approve_refund"},
        requires_approval=True,
        approval_message="Manager approval required.",
        approval_metadata={"minimum_role": "manager"},
    )
    def verify_policy(self) -> None:
        """Verify the policy against the current order."""

    step_definition = getattr(verify_policy, STEP_DEFINITION_ATTR)

    assert step_definition.name == "policy_check"
    assert step_definition.method_name == "verify_policy"
    assert step_definition.retries == 3
    assert step_definition.retry_on == (TimeoutError, ConnectionError)
    assert step_definition.retry_delay == 1.5
    assert step_definition.description == "Check whether the refund policy allows approval."
    assert step_definition.routes == {"approved": "approve_refund"}
    assert step_definition.requires_approval is True
    assert step_definition.approval_message == "Manager approval required."
    assert step_definition.approval_metadata == {"minimum_role": "manager"}
    assert verify_policy.__doc__ == "Verify the policy against the current order."


def test_workflow_collects_only_decorated_steps_in_declaration_order() -> None:
    """Workflow metadata should include decorated methods and preserve order."""

    @workflow
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            """Ensure the order exists."""

        def helper(self) -> None:
            """Non-step helpers should not be collected."""

        @step(name="policy_check")
        def verify_policy(self) -> None:
            """Ensure the policy allows a refund."""

    workflow_definition = getattr(RefundWorkflow, WORKFLOW_DEFINITION_ATTR)

    assert isinstance(workflow_definition, WorkflowDefinition)
    assert workflow_definition.name == "RefundWorkflow"
    assert workflow_definition.retries == 0
    assert workflow_definition.retry_on == ()
    assert workflow_definition.retry_delay == 0.0
    assert [step_definition.name for step_definition in workflow_definition.steps] == [
        "check_order",
        "policy_check",
    ]
    assert [step_definition.method_name for step_definition in workflow_definition.steps] == [
        "check_order",
        "verify_policy",
    ]
    assert [step_definition.order for step_definition in workflow_definition.steps] == [0, 1]
    assert not hasattr(RefundWorkflow.__dict__["helper"], STEP_DEFINITION_ATTR)


def test_workflow_configured_form_captures_workflow_defaults() -> None:
    """Configured workflow decoration should store workflow-level defaults."""

    @workflow(
        name="refund_workflow",
        retries=2,
        retry_on=(ConnectionError,),
        retry_delay=0.25,
    )
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            """Ensure the order exists."""

    workflow_definition = getattr(RefundWorkflow, WORKFLOW_DEFINITION_ATTR)

    assert workflow_definition.name == "refund_workflow"
    assert workflow_definition.retries == 2
    assert workflow_definition.retry_on == (ConnectionError,)
    assert workflow_definition.retry_delay == 0.25


def test_step_retry_metadata_preserves_none_and_explicit_values() -> None:
    """Step metadata should preserve omitted values for workflow inheritance."""

    @workflow
    class RefundWorkflow:
        @step
        def check_order(self) -> None:
            """Use workflow defaults."""

        @step(retries=1, retry_on=(TimeoutError,), retry_delay=0.5)
        def verify_policy(self) -> None:
            """Override workflow defaults."""

    step_definitions = getattr(RefundWorkflow, WORKFLOW_DEFINITION_ATTR).steps
    inherited_step, explicit_step = step_definitions

    assert inherited_step.retries is None
    assert inherited_step.retry_on is None
    assert inherited_step.retry_delay is None

    assert explicit_step.retries == 1
    assert explicit_step.retry_on == (TimeoutError,)
    assert explicit_step.retry_delay == 0.5


def test_top_level_decorator_exports_match_decorator_module() -> None:
    """The public package API should expose the implemented decorators."""
    assert agentflow.step is step
    assert agentflow.workflow is workflow
