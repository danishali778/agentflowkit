# Building Your First Workflow

## Purpose

This guide shows the simplest end-to-end way to build and run a workflow with
Agent Workflow Kit.

The current MVP is designed around:

- a state object
- a workflow class
- ordered `@step` methods
- a final `WorkflowResult`

## Step 1: Define a state object

The state object is the shared mutable data that all workflow steps read and
update.

Using a dataclass is the most natural pattern:

```python
from dataclasses import dataclass


@dataclass
class RefundState:
    order_id: str
    amount: float
    order_found: bool = False
    policy_ok: bool = False
    response_text: str = ""
```

In the current SDK, this state object is passed into `run(...)` and then made
available to steps as `self.state`.

## Step 2: Define a workflow class

Use `@workflow` on the class and `@step` on each ordered workflow step.

```python
from agentflow import step, workflow


@workflow
class RefundWorkflow:
    @step
    def check_order(self) -> str:
        self.state.order_found = True
        return f"Order {self.state.order_id} located."

    @step
    def verify_policy(self) -> str:
        self.state.policy_ok = self.state.order_found and self.state.amount <= 100.0
        return "Refund policy check completed."

    @step
    def generate_response(self) -> str:
        if self.state.policy_ok:
            self.state.response_text = f"Refund approved for {self.state.order_id}."
        else:
            self.state.response_text = f"Refund denied for {self.state.order_id}."
        return self.state.response_text
```

The important part is that steps run in the order they are declared.

## Step 3: Run the workflow

Create a workflow instance and pass in the initial state object.

```python
workflow_instance = RefundWorkflow()
result = workflow_instance.run(RefundState(order_id="ord_123", amount=42.50))
```

This returns a `WorkflowResult`.

## Step 4: Inspect the result

You can inspect both the final workflow state and the step-by-step execution
story.

```python
print(result.status.value)
print(result.state.response_text)

for step_result in result.steps:
    print(step_result.step_name, step_result.status.value, step_result.output)
```

## What happens during execution

At runtime, the current SDK does the following:

1. validates the workflow definition
2. validates the initial state
3. assigns the state object to `self.state`
4. runs each step in order
5. collects `StepResult` objects
6. returns one final `WorkflowResult`

## Best practices for a first workflow

For the current MVP, the best patterns are:

- keep the state object small and explicit
- let each step do one clear job
- use return values for readable step output
- use `self.state` for shared data between steps
- keep workflows linear and easy to follow

## See also

For a runnable version of this pattern, see:

- [../../examples/refund_workflow.py](../../examples/refund_workflow.py)
