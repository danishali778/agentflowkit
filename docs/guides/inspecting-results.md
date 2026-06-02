# Inspecting Results

## Purpose

This guide explains how to read the result objects returned by the current
Agent Workflow Kit runtime.

## The two result layers

The runtime currently returns:

- one `WorkflowResult`
- a list of `StepResult` objects inside it

Together, these tell you both the overall workflow outcome and the step-level
execution details.

## `WorkflowResult`

The workflow result contains the high-level execution summary.

Important fields include:

- `workflow_name`
- `state`
- `status`
- `steps`
- `error`
- `started_at`
- `finished_at`
- `duration_ms`

### Example

```python
result = workflow_instance.run(state)

print(result.workflow_name)
print(result.status.value)
print(result.duration_ms)
print(result.state)
```

## `StepResult`

Each executed step produces a `StepResult`.

Important fields include:

- `step_name`
- `status`
- `attempts`
- `output`
- `error`
- `started_at`
- `finished_at`
- `duration_ms`

### Example

```python
for step_result in result.steps:
    print(step_result.step_name)
    print(step_result.status.value)
    print(step_result.attempts)
    print(step_result.output)
    print(step_result.error)
```

## Reading success cases

In a successful workflow run, you will usually see:

- workflow status of `succeeded`
- step statuses of `succeeded`
- useful step outputs
- final state reflecting the decisions made by the workflow

## Reading failure cases

In a failed workflow run, you should usually inspect:

- `result.status`
- `result.error`
- the last `StepResult`
- the number of attempts on the failed step

This helps you answer:

- which step failed
- whether it retried
- what exception was raised
- what state had already been mutated before failure

## Example inspection pattern

```python
result = workflow_instance.run(state)

print("Workflow:", result.workflow_name)
print("Status:", result.status.value)

if result.error is not None:
    print("Workflow error:", result.error)

for step_result in result.steps:
    print(
        f"{step_result.step_name}: "
        f"{step_result.status.value} "
        f"(attempts={step_result.attempts}, output={step_result.output!r})"
    )
```

## Why structured results matter

The current MVP does not yet have dashboards or external tracing systems.

That makes `WorkflowResult` and `StepResult` especially important because they
are the main built-in observability surface of the SDK today.

## See also

For a working example that prints readable result data, see:

- [../../examples/support_triage.py](../../examples/support_triage.py)
- [../../examples/content_review.py](../../examples/content_review.py)
