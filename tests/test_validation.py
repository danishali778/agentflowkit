"""Behavior-focused tests for workflow validation and framework exceptions."""

import pytest

from agentflow.exceptions import (
    AgentFlowError,
    ApprovalRequiredError,
    RouteResolutionError,
    StateValidationError,
    StepExecutionError,
    WorkflowDefinitionError,
    WorkflowExecutionError,
)
from agentflow.models import END, StepDefinition, WorkflowDefinition
from agentflow.validation import (
    validate_initial_state,
    validate_step_definition,
    validate_step_method_signature,
    validate_workflow_definition,
)


def _build_valid_step(*, name: str = "check_order", order: int = 0) -> StepDefinition:
    """Create a valid step definition that tests can customize."""
    return StepDefinition(name=name, method_name=name, order=order)


def test_framework_exceptions_follow_the_documented_hierarchy() -> None:
    """All framework exceptions should inherit from the common base class."""
    assert issubclass(WorkflowDefinitionError, AgentFlowError)
    assert issubclass(StateValidationError, AgentFlowError)
    assert issubclass(StepExecutionError, AgentFlowError)
    assert issubclass(WorkflowExecutionError, AgentFlowError)
    assert issubclass(RouteResolutionError, AgentFlowError)
    assert issubclass(ApprovalRequiredError, AgentFlowError)


def test_valid_workflow_definition_is_returned_unchanged() -> None:
    """A valid workflow definition should pass and be returned as-is."""
    definition = WorkflowDefinition(
        name="refund_workflow",
        steps=[_build_valid_step(name="check_order", order=0)],
    )

    assert validate_workflow_definition(definition) is definition


def test_empty_workflow_definition_raises_clear_error() -> None:
    """Workflows without steps should fail validation."""
    definition = WorkflowDefinition(name="refund_workflow", steps=[])

    with pytest.raises(WorkflowDefinitionError, match="at least one step"):
        validate_workflow_definition(definition)


def test_duplicate_step_names_raise_definition_error() -> None:
    """Duplicate step names should be rejected early."""
    definition = WorkflowDefinition(
        name="refund_workflow",
        steps=[
            _build_valid_step(name="check_order", order=0),
            _build_valid_step(name="check_order", order=1),
        ],
    )

    with pytest.raises(WorkflowDefinitionError, match="Duplicate step name"):
        validate_workflow_definition(definition)


def test_negative_retry_counts_raise_definition_errors() -> None:
    """Workflow and step retry counts must stay non-negative."""
    invalid_workflow = WorkflowDefinition(
        name="refund_workflow",
        steps=[_build_valid_step()],
        retries=-1,
    )
    invalid_step = StepDefinition(
        name="check_order",
        method_name="check_order",
        order=0,
        retries=-1,
    )

    with pytest.raises(WorkflowDefinitionError, match="Workflow retry count"):
        validate_workflow_definition(invalid_workflow)
    with pytest.raises(WorkflowDefinitionError, match="Step retry count"):
        validate_step_definition(invalid_step)


def test_invalid_retry_on_shapes_raise_definition_errors() -> None:
    """Retry exception metadata must be tuples of exception classes."""
    invalid_workflow = WorkflowDefinition(
        name="refund_workflow",
        steps=[_build_valid_step()],
        retry_on=(TimeoutError, "ConnectionError"),
    )
    invalid_step = StepDefinition(
        name="check_order",
        method_name="check_order",
        order=0,
        retry_on=("TimeoutError",),
    )

    with pytest.raises(WorkflowDefinitionError, match="Workflow retry_on"):
        validate_workflow_definition(invalid_workflow)
    with pytest.raises(WorkflowDefinitionError, match="Step retry_on"):
        validate_step_definition(invalid_step)


def test_negative_retry_delays_raise_definition_errors() -> None:
    """Retry delays must stay non-negative when provided."""
    invalid_workflow = WorkflowDefinition(
        name="refund_workflow",
        steps=[_build_valid_step()],
        retry_delay=-0.1,
    )
    invalid_step = StepDefinition(
        name="check_order",
        method_name="check_order",
        order=0,
        retry_delay=-0.1,
    )

    with pytest.raises(WorkflowDefinitionError, match="Workflow retry_delay"):
        validate_workflow_definition(invalid_workflow)
    with pytest.raises(WorkflowDefinitionError, match="Step retry_delay"):
        validate_step_definition(invalid_step)


def test_invalid_step_order_and_reserved_step_name_fail_validation() -> None:
    """Reserved names and negative order should be rejected."""
    invalid_order_step = StepDefinition(name="check_order", method_name="check_order", order=-1)
    reserved_name_step = StepDefinition(name="run", method_name="run", order=0)
    reserved_method_name_step = StepDefinition(name="generate_response", method_name="run", order=0)

    with pytest.raises(WorkflowDefinitionError, match="order"):
        validate_step_definition(invalid_order_step)
    with pytest.raises(WorkflowDefinitionError, match="reserved"):
        validate_step_definition(reserved_name_step)
    with pytest.raises(WorkflowDefinitionError, match="method name"):
        validate_step_definition(reserved_method_name_step)


def test_invalid_route_metadata_raises_definition_errors() -> None:
    """Route mappings must use non-empty string keys and valid targets."""
    empty_routes = StepDefinition(
        name="evaluate_refund",
        method_name="evaluate_refund",
        order=0,
        routes={},
    )
    invalid_key = StepDefinition(
        name="evaluate_refund",
        method_name="evaluate_refund",
        order=0,
        routes={"": "approve_refund"},
    )
    invalid_target = StepDefinition(
        name="evaluate_refund",
        method_name="evaluate_refund",
        order=0,
        routes={"approved": ""},
    )

    with pytest.raises(WorkflowDefinitionError, match="must not be empty"):
        validate_step_definition(empty_routes)
    with pytest.raises(WorkflowDefinitionError, match="route keys"):
        validate_step_definition(invalid_key)
    with pytest.raises(WorkflowDefinitionError, match="route targets"):
        validate_step_definition(invalid_target)


def test_invalid_approval_metadata_raises_definition_errors() -> None:
    """Approval configuration should reject malformed metadata."""
    invalid_requires_approval = StepDefinition(
        name="approve_refund",
        method_name="approve_refund",
        order=0,
        requires_approval="yes",
    )
    invalid_message = StepDefinition(
        name="approve_refund",
        method_name="approve_refund",
        order=0,
        requires_approval=True,
        approval_message="",
    )
    invalid_metadata = StepDefinition(
        name="approve_refund",
        method_name="approve_refund",
        order=0,
        requires_approval=True,
        approval_metadata=("minimum_role", "manager"),
    )

    with pytest.raises(WorkflowDefinitionError, match="requires_approval"):
        validate_step_definition(invalid_requires_approval)
    with pytest.raises(WorkflowDefinitionError, match="approval_message"):
        validate_step_definition(invalid_message)
    with pytest.raises(WorkflowDefinitionError, match="approval_metadata"):
        validate_step_definition(invalid_metadata)


def test_route_targets_must_exist_and_point_forward() -> None:
    """Route targets should reference later public step names or END."""
    routed_step = StepDefinition(
        name="evaluate_refund",
        method_name="evaluate_refund",
        order=0,
        routes={"approved": "approve_refund", "done": END},
    )
    approve_step = StepDefinition(
        name="approve_refund",
        method_name="approve_refund",
        order=1,
    )
    valid_definition = WorkflowDefinition(
        name="refund_workflow",
        steps=[routed_step, approve_step],
    )

    assert validate_workflow_definition(valid_definition) is valid_definition

    unknown_target = WorkflowDefinition(
        name="refund_workflow",
        steps=[
            StepDefinition(
                name="evaluate_refund",
                method_name="evaluate_refund",
                order=0,
                routes={"approved": "missing_step"},
            ),
            approve_step,
        ],
    )
    self_route = WorkflowDefinition(
        name="refund_workflow",
        steps=[
            StepDefinition(
                name="evaluate_refund",
                method_name="evaluate_refund",
                order=0,
                routes={"again": "evaluate_refund"},
            )
        ],
    )
    backward_route = WorkflowDefinition(
        name="refund_workflow",
        steps=[
            StepDefinition(name="check_order", method_name="check_order", order=0),
            StepDefinition(
                name="evaluate_refund",
                method_name="evaluate_refund",
                order=1,
                routes={"restart": "check_order"},
            ),
        ],
    )

    with pytest.raises(WorkflowDefinitionError, match="does not match"):
        validate_workflow_definition(unknown_target)
    with pytest.raises(WorkflowDefinitionError, match="later step"):
        validate_workflow_definition(self_route)
    with pytest.raises(WorkflowDefinitionError, match="later step"):
        validate_workflow_definition(backward_route)


def test_valid_step_method_signatures_are_supported() -> None:
    """The MVP should allow step(self) and step(self, context)."""

    def check_order(self) -> None:
        """Accept the minimal step signature."""

    def verify_policy(self, context) -> None:
        """Accept the optional context signature."""

    validate_step_method_signature(check_order)
    validate_step_method_signature(verify_policy)


def test_invalid_step_method_signatures_raise_definition_error() -> None:
    """Unsupported step signatures should fail with a framework error."""

    def no_self() -> None:
        """Missing the workflow instance parameter."""

    def too_many(self, context, extra) -> None:
        """Contains too many positional parameters."""

    def keyword_only(self, *, context) -> None:
        """Uses unsupported keyword-only parameters."""

    async def async_step(self) -> None:
        """Async step methods are out of scope for the MVP."""

    with pytest.raises(WorkflowDefinitionError, match="workflow instance parameter"):
        validate_step_method_signature(no_self)
    with pytest.raises(WorkflowDefinitionError, match="only the workflow instance"):
        validate_step_method_signature(too_many)
    with pytest.raises(WorkflowDefinitionError, match="only use positional parameters"):
        validate_step_method_signature(keyword_only)
    with pytest.raises(WorkflowDefinitionError, match="synchronous functions"):
        validate_step_method_signature(async_step)


def test_validate_initial_state_rejects_none_and_returns_objects() -> None:
    """State validation should be intentionally light in Phase 3."""
    state = {"order_id": "ord_123"}

    with pytest.raises(StateValidationError, match="must not be None"):
        validate_initial_state(None)

    assert validate_initial_state(state) is state
