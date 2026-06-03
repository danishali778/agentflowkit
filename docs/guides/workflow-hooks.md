# Workflow Hooks

## Purpose

Workflow hooks let you observe workflow execution without changing workflow
logic.

Hooks are synchronous callbacks. They are useful for local logging, metrics,
debugging, and lightweight tracing experiments.

They are not a dashboard, async event bus, persistence system, or external
observability backend.

## Basic hook shape

A hook is any callable that accepts one workflow event.

```python
from agentflow import WorkflowEvent


def log_event(event: WorkflowEvent) -> None:
    print(type(event).__name__, event)
```

Pass hooks to `run(...)`:

```python
result = workflow_instance.run(state, hooks=[log_event])
```

Hook return values are ignored.

## Event types

The public event types are:

- `WorkflowStartedEvent`
- `StepStartedEvent`
- `StepFinishedEvent`
- `WorkflowFinishedEvent`

`WorkflowEvent` is the union of those event types.

## Event order

For a successful two-step workflow, events are emitted in this order:

1. `WorkflowStartedEvent`
2. `StepStartedEvent`
3. `StepFinishedEvent`
4. `StepStartedEvent`
5. `StepFinishedEvent`
6. `WorkflowFinishedEvent`

Step events are emitted once per logical step visit.

For retried steps, `StepStartedEvent` is emitted once before retry handling, and
`StepFinishedEvent` contains the final attempt count.

For routed workflows, skipped steps do not emit step events because they were
not visited.

## Step results in hooks

`StepFinishedEvent.result` is the final `StepResult` for that step.

That means hooks can inspect:

- status
- attempts
- output
- error
- route fields
- approval decision fields

## Workflow results in hooks

`WorkflowFinishedEvent.result` is the final `WorkflowResult`.

This lets a hook inspect the same result the caller receives from `run(...)`.

## Hook failures

Hook failures are explicit.

If a hook raises an exception, the workflow fails with `HookExecutionError`.

If `raise_on_failure=True` is used, that hook failure is wrapped in
`WorkflowExecutionError` at the workflow boundary.

Hook callbacks are synchronous and are not retried.

## See also

For a runnable example, see:

- [../../examples/workflow_hooks.py](../../examples/workflow_hooks.py)
