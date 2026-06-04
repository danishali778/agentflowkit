# Workflow Composition

Workflow composition lets one workflow run another workflow from inside a step.

This is useful when a parent workflow owns the larger process, but a smaller
child workflow already knows how to handle one part of the work.

Composition in Agent Workflow Kit is synchronous and callback-free. It is not a
queue, worker system, durable orchestration engine, or async scheduler.

## Basic example

Use a context-aware step and call `context.run_child(...)`.

```python
from dataclasses import dataclass

from agentflow import RunContext, step, workflow


@dataclass
class RefundState:
    amount: float
    approved: bool = False


@workflow
class RefundWorkflow:
    @step
    def approve_refund(self) -> None:
        self.state.approved = self.state.amount <= 100.0


@dataclass
class TicketState:
    refund: RefundState
    refund_status: str = ""


@workflow
class SupportWorkflow:
    @step
    def process_refund(self, context: RunContext) -> None:
        child_result = context.run_child(RefundWorkflow(), self.state.refund)
        self.state.refund_status = child_result.status.value
```

The child workflow runs immediately. The parent step waits for it to finish.

## Result inspection

Child workflow results are recorded on the parent step:

```python
result = SupportWorkflow().run(TicketState(refund=RefundState(amount=25.0)))

parent_step = result.steps[0]
child_result = parent_step.child_workflows[0]

print(child_result.workflow_name)
print(child_result.status.value)
```

Each child result is a normal `WorkflowResult`, with its own:

- final status
- child state
- step results
- errors
- route trace
- timing information

## Failure behavior

By default, a failed child workflow fails the parent step.

```python
context.run_child(RefundWorkflow(), self.state.refund)
```

If the child workflow fails, the parent step fails with
`ChildWorkflowExecutionError`. The failed child result is still available in
`StepResult.child_workflows`.

If the parent wants to inspect the failed child and continue, opt out of
fail-fast behavior:

```python
child_result = context.run_child(
    RefundWorkflow(),
    self.state.refund,
    fail_parent_on_failure=False,
)

if child_result.status.value == "failed":
    self.state.refund_status = "needs manual review"
```

## Hooks and approvals

Child workflows inherit parent hooks and approval handlers by default.

That means:

- child workflow events are emitted through the same hooks
- approval-gated child steps use the same approval handler
- child workflow results remain separate from parent workflow results

You can pass different hooks to `context.run_child(...)` when you need child
workflow-specific observation.

## What composition does not do

Composition does not make workflows durable or distributed.

The current runtime does not:

- persist child workflow state
- resume child workflows later
- run child workflows in parallel
- schedule child workflows in workers
- show dynamic child calls in static graph export

Graph export remains metadata-only. It can show declared steps, routes,
approval-gated steps, and terminal paths, but it does not inspect runtime calls
to `context.run_child(...)`.
