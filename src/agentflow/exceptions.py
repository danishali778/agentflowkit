"""Framework-specific exception types for Agent Workflow Kit.

The framework distinguishes between definition-time problems, execution
failures, and invalid runtime inputs so callers can reason about failures
without parsing generic Python exceptions.
"""


class AgentFlowError(Exception):
    """Base class for framework-specific Agent Workflow Kit errors."""


class WorkflowDefinitionError(AgentFlowError):
    """Raised when a workflow or step definition violates SDK rules."""


class StepExecutionError(AgentFlowError):
    """Reserved for future step-level execution wrappers.

    The current MVP keeps the original business exception on ``StepResult``
    rather than wrapping it, but this type remains part of the documented
    framework hierarchy for later phases.
    """


class WorkflowExecutionError(AgentFlowError):
    """Raised when a failed workflow is re-raised at the workflow boundary."""


class StateValidationError(AgentFlowError):
    """Raised when a workflow receives invalid initial state."""


class RouteResolutionError(AgentFlowError):
    """Raised when a routed step returns an invalid route decision."""


class ApprovalRequiredError(AgentFlowError):
    """Raised when an approval-gated step cannot obtain approval."""


class HookExecutionError(AgentFlowError):
    """Raised when a workflow lifecycle hook fails."""


class ChildWorkflowExecutionError(AgentFlowError):
    """Raised when a child workflow failure stops a parent step."""
