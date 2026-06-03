"""Top-level package for Agent Workflow Kit.

This module defines the first stable top-level public API for the MVP runtime
so users can import the main workflow primitives from ``agentflow`` directly.
"""

from agentflow.decorators import step, workflow
from agentflow.exceptions import (
    AgentFlowError,
    ApprovalRequiredError,
    RouteResolutionError,
    StateValidationError,
    StepExecutionError,
    WorkflowDefinitionError,
    WorkflowExecutionError,
)
from agentflow.models import (
    END,
    ApprovalDecision,
    ApprovalRequest,
    RouteDecision,
    StepResult,
    WorkflowResult,
)
from agentflow.retry import RetryPolicy

__version__ = "0.1.0"

__all__ = [
    "AgentFlowError",
    "ApprovalDecision",
    "ApprovalRequest",
    "ApprovalRequiredError",
    "END",
    "RouteDecision",
    "RouteResolutionError",
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
]
