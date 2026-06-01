# Agent Workflow Kit

Agent Workflow Kit is an open-source Python SDK for building agent workflows with plain
Python classes, step decorators, shared state, and reliable execution primitives.

## Status

The MVP runtime is implemented. You can define workflows with `@workflow` and `@step`,
run them with shared mutable state, configure retries, and inspect structured workflow
and step results.

## Why this project exists

Many useful agent workflows do not need graph-first complexity on day one. This project
aims to provide a simpler, beginner-friendly SDK for linear workflows that still gives
developers real execution structure.

The MVP is planned to focus on:

- workflow classes
- step decorators
- ordered execution
- shared state
- retries
- structured results

## Current feature set

- workflow classes with `@workflow`
- step registration with `@step`
- shared mutable state through `self.state`
- ordered synchronous execution
- retry handling for transient failures
- structured `WorkflowResult` and `StepResult`
- optional `raise_on_failure=True`

## Installation

```bash
pip install -e .[dev]
```

## Quickstart

```python
from dataclasses import dataclass

from agentflow import workflow, step


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
    def check_order(self):
        self.state.order_found = True

    @step
    def verify_policy(self):
        self.state.policy_ok = self.state.amount <= 100.0

    @step
    def generate_response(self):
        if self.state.policy_ok:
            self.state.response_text = f"Refund approved for {self.state.order_id}."
        else:
            self.state.response_text = f"Refund denied for {self.state.order_id}."


workflow_instance = RefundWorkflow()
result = workflow_instance.run(RefundState(order_id="ord_123", amount=42.50))

print(result.status.value)
print(result.state.response_text)
print(result.steps[-1].output)
```

## Example guides

### Refund workflow

The refund example shows the simplest happy path:
- linear step execution
- state mutation across steps
- final message generation from earlier decisions

Run it with:

```bash
python examples/refund_workflow.py
```

See: [examples/refund_workflow.py](examples/refund_workflow.py)

### Support triage workflow

The support triage example shows:
- a typed state object for a support ticket
- use of the optional step `context`
- queue assignment based on computed priority
- readable inspection of per-step results

Run it with:

```bash
python examples/support_triage.py
```

See: [examples/support_triage.py](examples/support_triage.py)

### Content review workflow

The content review example shows:
- a retrying moderation step
- transient failure recovery with `TimeoutError`
- final result inspection including attempt counts

Run it with:

```bash
python examples/content_review.py
```

See: [examples/content_review.py](examples/content_review.py)

## Repository layout

The repository uses a `src/` layout and keeps design decisions in `docs/`.

- `docs/` contains architecture, API, startup, scaling, and workflow guidance.
- `src/agentflow/` contains the SDK implementation.
- `tests/` contains behavior-focused test coverage.
- `examples/` contains runnable workflow examples.
- `.github/workflows/` contains CI and release automation.

## Development

The project targets Python `3.11+`.

### Run checks

```bash
ruff check .
pytest
```

### Run examples

```bash
python examples/refund_workflow.py
python examples/support_triage.py
python examples/content_review.py
```

## Documentation

Start with the docs index:

- [docs/README.md](docs/README.md)

The current source of truth for architecture and implementation direction lives in:

- `docs/00-project-definition.md`
- `docs/01-mvp-architecture.md`
- `docs/02-python-api.md`
- `docs/03-package-structure.md`
- `docs/08-implementation-plan.md`

## Roadmap

The initial build will focus on the documented MVP before any advanced features such as:

- branching
- human approval steps
- adapters
- dashboards
- worker systems

Those remain future work by design.
