# Agent Workflow Kit

Agent Workflow Kit is an open-source Python SDK for building agent workflows
with plain Python classes, step decorators, shared state, retries, structured
execution results, and metadata-only graph export.

## Status

The main MVP is implemented.

Today, the SDK already supports:

- workflow classes with `@workflow`
- ordered step methods with `@step`
- shared mutable state through `self.state`
- synchronous execution
- retry handling for transient failures
- conditional branching with explicit route maps
- synchronous human approval callbacks
- synchronous lifecycle hooks for logging and observability
- workflow graph export as Mermaid diagrams
- structured `WorkflowResult` and `StepResult`
- optional `raise_on_failure=True`

This makes the project useful today for linear agent-style workflows such as:

- refund handling
- support triage
- content review
- branching refund decisions
- approval-gated refund decisions
- hook-based execution logging
- workflow graph inspection
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
- conditional routing to later steps or `END`
- human approval callbacks before selected steps run
- lifecycle hooks for workflow and step events
- step-level retries with fixed delay
- validation for workflow definitions and step signatures
- framework-specific exceptions
- workflow and step timing information
- per-step outputs, errors, and attempt counts
- metadata-only workflow graph export with Mermaid rendering

The public `agentflow` package currently exposes:

- `workflow`
- `step`
- `WorkflowResult`
- `StepResult`
- `RetryPolicy`
- `END`
- `ApprovalRequest`
- `ApprovalDecision`
- `RouteDecision`
- `WorkflowStartedEvent`
- `StepStartedEvent`
- `StepFinishedEvent`
- `WorkflowFinishedEvent`
- `WorkflowEvent`
- `WorkflowHook`
- `WorkflowGraph`
- `WorkflowGraphNode`
- `WorkflowGraphEdge`
- `export_workflow_graph`
- `HookExecutionError`
- `ApprovalRequiredError`
- `RouteResolutionError`
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

### Branching refund workflow

This example shows:

- route-based branching from a decision step
- explicit terminal paths with `END`
- route trace inspection
- skipped step results

Run it with:

```bash
python examples/branching_refund_workflow.py
```

See: [examples/branching_refund_workflow.py](examples/branching_refund_workflow.py)

### Approval refund workflow

This example shows:

- a synchronous approval handler
- approval request metadata
- approved and denied approval decisions
- approval details recorded on `StepResult`

Run it with:

```bash
python examples/approval_refund_workflow.py
```

See: [examples/approval_refund_workflow.py](examples/approval_refund_workflow.py)

### Workflow hooks

This example shows:

- synchronous lifecycle hooks
- workflow and step event logging
- normal result inspection after hooks run

Run it with:

```bash
python examples/workflow_hooks.py
```

See: [examples/workflow_hooks.py](examples/workflow_hooks.py)

### Graph export workflow

This example shows:

- graph export from workflow metadata
- Mermaid rendering without running the workflow
- route edges, approval-gated nodes, and terminal `END` paths

Run it with:

```bash
python examples/graph_export.py
```

See: [examples/graph_export.py](examples/graph_export.py)

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
python examples/branching_refund_workflow.py
python examples/approval_refund_workflow.py
python examples/workflow_hooks.py
python examples/graph_export.py
```

## Repository layout

The repository uses a `src/` layout.

- `src/agentflow/` contains the SDK implementation
- `tests/` contains behavior-focused tests
- `examples/` contains runnable example workflows
- `.github/workflows/` contains CI and release validation
- `docs/` contains deeper public documentation, including current status,
  architecture, and usage guides

## Documentation

If you want a high-level current-state summary, start with:

- [docs/current-status.md](docs/current-status.md)

If you want the broader public docs index, start with:

- [docs/README.md](docs/README.md)

If you want deeper technical documentation, start with:

- [docs/architecture/README.md](docs/architecture/README.md)
- [docs/guides/README.md](docs/guides/README.md)

## Not implemented yet

The current SDK does not yet include:

- async execution
- persistent approval pause/resume
- async event buses or tracing backends
- worker backends
- dashboards or interactive visual editors
- graph execution
- framework adapters such as LangGraph integration

Those remain future extensions beyond the current MVP.

## Roadmap direction

The next stage of the project is not "finish the MVP."

The likely next areas of work are:

- release hardening
- repository and contributor polish
- docs hardening
- post-MVP features such as persistent approvals or async execution
