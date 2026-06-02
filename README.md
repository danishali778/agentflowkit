# Agent Workflow Kit

Agent Workflow Kit is an open-source Python SDK for building agent workflows
with plain Python classes, step decorators, shared state, retries, and
structured execution results.

## Status

The main MVP is implemented.

Today, the SDK already supports:

- workflow classes with `@workflow`
- ordered step methods with `@step`
- shared mutable state through `self.state`
- synchronous execution
- retry handling for transient failures
- structured `WorkflowResult` and `StepResult`
- optional `raise_on_failure=True`

This makes the project useful today for linear agent-style workflows such as:

- refund handling
- support triage
- content review
- internal multi-step automations

## Why this project exists

Many useful agent workflows do not need graph-first complexity on day one.

Agent Workflow Kit is meant to provide a simpler path:

- more structure than ad hoc scripts
- less framework overhead than graph-first orchestration tools
- a class-based Python authoring model that is easy to teach and debug

## Quickstart

```python
from dataclasses import dataclass

from agentflow import step, workflow


@dataclass
class RefundState:
    order_id: str
    amount: float
    order_found: bool = False
    policy_ok: bool = False
    response_text: str = ""


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


workflow_instance = RefundWorkflow()
result = workflow_instance.run(RefundState(order_id="ord_123", amount=42.50))

print(result.status.value)
print(result.state.response_text)
print(result.steps[-1].output)
```

## Current capabilities

The current SDK already gives you:

- a decorator-based authoring model
- ordered workflow execution
- step-level retries with fixed delay
- validation for workflow definitions and step signatures
- framework-specific exceptions
- workflow and step timing information
- per-step outputs, errors, and attempt counts

The public `agentflow` package currently exposes:

- `workflow`
- `step`
- `WorkflowResult`
- `StepResult`
- `RetryPolicy`
- framework exception types

## Examples

The repository includes runnable examples under `examples/`.

### Refund workflow

This example shows the simplest happy path:

- linear step execution
- state mutation across steps
- a final response generated from earlier decisions

Run it with:

```bash
python examples/refund_workflow.py
```

See: [examples/refund_workflow.py](examples/refund_workflow.py)

### Support triage workflow

This example shows:

- a typed support-ticket state object
- the optional step context parameter
- queue assignment from computed workflow state
- readable inspection of per-step results

Run it with:

```bash
python examples/support_triage.py
```

See: [examples/support_triage.py](examples/support_triage.py)

### Content review workflow

This example shows:

- a retrying moderation step
- transient failure recovery with `TimeoutError`
- final decision output and attempt counts

Run it with:

```bash
python examples/content_review.py
```

See: [examples/content_review.py](examples/content_review.py)

## Installation

For local development:

```bash
pip install -e .[dev]
```

The project currently targets Python `3.11+`.

## Development

Run the local checks with:

```bash
ruff check .
pytest
```

Run the examples with:

```bash
python examples/refund_workflow.py
python examples/support_triage.py
python examples/content_review.py
```

## Repository layout

The repository uses a `src/` layout.

- `src/agentflow/` contains the SDK implementation
- `tests/` contains behavior-focused tests
- `examples/` contains runnable example workflows
- `.github/workflows/` contains CI and release validation
- `docs/` contains deeper project, architecture, and roadmap material

## Documentation

If you want a high-level current-state summary, start with:

- [docs/09-current-project-status.md](docs/09-current-project-status.md)

If you want the deeper architecture and planning material, start with:

- [docs/README.md](docs/README.md)

## Not implemented yet

The current SDK does not yet include:

- branching or conditional routing
- human approval steps
- async execution
- worker backends
- dashboards or workflow visualization
- framework adapters such as LangGraph integration

Those remain future extensions beyond the current MVP.

## Roadmap direction

The next stage of the project is not "finish the MVP."

The likely next areas of work are:

- release hardening
- repository and contributor polish
- docs hardening
- post-MVP features such as branching or approval steps
