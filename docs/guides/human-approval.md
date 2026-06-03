# Human Approval

Human approval lets a workflow ask an external callback for permission before a
selected step runs.

This is synchronous in the current SDK. It is useful for local scripts,
services, and tests where the caller can make the approval decision during the
workflow run.

## Basic shape

Mark a step with `requires_approval=True`.

```python
from agentflow import ApprovalDecision, ApprovalRequest, step, workflow


@workflow
class RefundWorkflow:
    @step(
        requires_approval=True,
        approval_message="High-value refund requires manager approval.",
        approval_metadata={"minimum_role": "manager"},
    )
    def approve_refund(self) -> None:
        self.state.approved = True


def approve(request: ApprovalRequest) -> ApprovalDecision:
    return ApprovalDecision(approved=True, reason="Approved by manager.")


result = RefundWorkflow().run(state, approval_handler=approve)
```

## Approval requests

The approval handler receives an `ApprovalRequest`.

It includes:

- `workflow_name`
- `step_name`
- `run_id`
- `state`
- `message`
- `metadata`

The request uses the same shared state object that workflow steps use.

## Approval decisions

The handler can return an `ApprovalDecision`.

```python
ApprovalDecision(
    approved=True,
    reason="Within policy.",
    metadata={"approver": "sam"},
)
```

For simple cases, the handler may also return a boolean:

- `True` means approved
- `False` means denied

Boolean responses are normalized into `ApprovalDecision` objects in the
recorded step result.

## Denied approvals

If approval is denied:

- the step method is not called
- the step result is marked failed
- the workflow stops
- the workflow error is `ApprovalRequiredError`

This makes denial explicit and inspectable without pretending the business step
ran.

## Missing handlers

If a workflow reaches an approval-gated step and no `approval_handler` was
provided, the workflow fails with `ApprovalRequiredError`.

If `raise_on_failure=True` is used, that failure is wrapped in
`WorkflowExecutionError` and the original approval error is preserved as the
cause.

## Result inspection

Approval details are recorded on `StepResult`.

Useful fields include:

- `approval_required`
- `approval_decision`
- `status`
- `attempts`
- `error`

Approval happens before the step method is invoked. If approval is missing,
denied, or the handler fails, the step method attempt count remains `0`.

## Approval and branching

Approval works with routed steps.

If approval succeeds, the step method runs and can return a route key as usual.

If approval is denied, route resolution does not happen and routed downstream
steps are marked skipped.

## Current limits

The current approval model does not provide:

- persistence
- async waiting
- resume tokens
- background workers
- an approval UI

Those are future orchestration features. The current feature is intentionally a
small callback primitive.
