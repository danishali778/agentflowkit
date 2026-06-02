# Retries And Failures

## Purpose

This guide explains how the current MVP handles transient failures, retry
behavior, and workflow failure outcomes.

## Retry model

The current runtime supports fixed-delay retries for synchronous step
execution.

Retry configuration can come from:

- workflow-level defaults
- step-level overrides

If a step leaves a retry field as `None`, the workflow-level value is used. If
the step provides an explicit value, it overrides the workflow default.

## Step-level retry example

```python
from agentflow import step, workflow


@workflow
class ContentReviewWorkflow:
    @step(retries=2, retry_on=(TimeoutError,), retry_delay=0.1)
    def moderate_content(self) -> str:
        ...
```

This means:

- the step may be retried up to 2 times after failure
- only `TimeoutError` triggers retry
- each retry waits `0.1` seconds

## What counts as a retryable failure

In the current SDK, a failed attempt is retried only when both of these are
true:

- the current attempt count is still within the configured retry limit
- the raised exception matches one of the configured `retry_on` exception types

If either condition fails, the runtime stops retrying that step.

## Failure behavior

The current runtime is fail-fast.

That means:

- a permanently failing step ends workflow execution
- later steps are not executed
- the workflow result is marked failed

There is no branching, compensation, or resume behavior in the current MVP.

## `raise_on_failure`

The public `run(...)` entry point supports:

```python
result = workflow_instance.run(state, raise_on_failure=False)
```

### When `raise_on_failure=False`

The runtime returns a failed `WorkflowResult`.

This is useful when you want to inspect:

- the final failure status
- the error object
- the steps that ran before failure

### When `raise_on_failure=True`

The runtime raises `WorkflowExecutionError` after the workflow fails.

This is useful when your application wants workflow failure to behave more like
an exception boundary.

## Practical example

The content review example demonstrates a transient moderation failure followed
by retry and eventual success.

See:

- [../../examples/content_review.py](../../examples/content_review.py)

## Best practices

For the current MVP:

- use retries only for transient failures
- keep retry counts small
- restrict `retry_on` to expected exception types
- use returned results for inspection when you want execution details
- use `raise_on_failure=True` when failure should immediately interrupt the caller
