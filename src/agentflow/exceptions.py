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
