"""Compatibility wrapper for approval controls."""

from agentflow.controls.approvals import (
    ApprovalHandler,
    build_approval_request,
    normalize_approval_decision,
    request_step_approval,
)

__all__ = [
    "ApprovalHandler",
    "build_approval_request",
    "normalize_approval_decision",
    "request_step_approval",
]
