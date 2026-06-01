"""Retry policy helpers for step execution.

This module isolates retry configuration resolution from the executor so
workflow orchestration can stay focused on running steps and building results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from agentflow.models import StepDefinition, WorkflowDefinition


@dataclass(slots=True)
class RetryPolicy:
    """Represents the effective retry policy for a single step execution."""

    retries: int
    retry_on: tuple[type[BaseException], ...]
    delay: float


def resolve_retry_policy(
    workflow_definition: WorkflowDefinition,
    step_definition: StepDefinition,
) -> RetryPolicy:
    """Resolve the effective retry policy for a step.

    Step-level ``None`` values inherit the workflow defaults documented by the
    MVP API, while explicit step values override them.
    """
    return RetryPolicy(
        retries=(
            workflow_definition.retries
            if step_definition.retries is None
            else step_definition.retries
        ),
        retry_on=(
            workflow_definition.retry_on
            if step_definition.retry_on is None
            else step_definition.retry_on
        ),
        delay=(
            workflow_definition.retry_delay
            if step_definition.retry_delay is None
            else step_definition.retry_delay
        ),
    )


def should_retry(policy: RetryPolicy, error: Exception, attempt: int) -> bool:
    """Return whether a failed attempt should be retried."""
    if attempt > policy.retries:
        return False
    if not policy.retry_on:
        return False

    return isinstance(error, policy.retry_on)


def sleep_for_retry(delay: float) -> None:
    """Pause between retry attempts when a fixed delay is configured."""
    if delay > 0:
        time.sleep(delay)
