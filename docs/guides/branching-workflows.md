# Branching Workflows

## Purpose

This guide explains how to use conditional branching in Agent Workflow Kit.

Branching lets one step choose a later step, or end the workflow early, while
keeping the current class-and-decorator authoring model.

## Basic route shape

Use `routes` on `@step` when a step should choose the next path.

```python
from agentflow import END, step, workflow


@workflow
class RefundWorkflow:
    @step(routes={"approved": "approve_refund", "denied": "deny_refund"})
    def evaluate_request(self) -> str:
        return "approved" if self.state.policy_ok else "denied"

    @step(routes={"done": END})
    def approve_refund(self) -> str:
        self.state.status = "approved"
        return "done"

    @step(routes={"done": END})
    def deny_refund(self) -> str:
        self.state.status = "denied"
        return "done"
```

The routed step returns a string route key. The runtime looks up that key in the
step's route map.

## Route targets

Route targets can be:

- the public name of a later step
- `END`

Routes are forward-only in the current implementation. A routed step cannot
route to itself or to an earlier step.

## Ending a workflow

Use `END` when a route should complete the workflow successfully.

```python
@step(routes={"done": END})
def archive_ticket(self) -> str:
    self.state.archived = True
    return "done"
```

This keeps terminal paths explicit and easy to validate.

## Result inspection

Branching adds route inspection data to the normal result objects.

`WorkflowResult.route_trace` records each route decision:

```python
for decision in result.route_trace:
    print(decision.step_name, decision.route_key, decision.next_step, decision.ended)
```

`StepResult` also includes route-related fields:

- `route_key`
- `next_step`
- `skipped_reason`

When a branch skips declared steps, those steps appear with `status` set to
`skipped` and `attempts` set to `0`.

## Route failures

If a routed step returns an unknown key or a non-string route key, the workflow
fails with `RouteResolutionError`.

With `raise_on_failure=True`, that route error is wrapped in
`WorkflowExecutionError` at the workflow boundary.

## See also

For a runnable example, see:

- [../../examples/branching_refund_workflow.py](../../examples/branching_refund_workflow.py)
