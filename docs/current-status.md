# Current Project Status

## Summary

Agent Workflow Kit is currently a working MVP Python SDK for building linear
and conditional agent workflows with plain Python classes and decorators.

The project is no longer at the scaffold or design-only stage. The core runtime
exists, the main developer-facing API is implemented, the examples are runnable,
and the repository already includes tests plus CI/release validation workflows.

In its current form, the SDK is best understood as a lightweight workflow layer
for small to medium agent-style automations where you want:

- more structure than ad hoc scripts
- less framework overhead than graph-first orchestration systems
- a class-based Python authoring model that is easy to teach, debug, and extend

## What the project supports today

The current MVP supports a clear and usable workflow authoring model:

- workflow classes declared with `@workflow`
- ordered workflow methods declared with `@step`
- shared mutable state stored on `self.state`
- synchronous step-by-step execution
- conditional routing from one step to a later step or `END`
- synchronous human approval callbacks before selected steps run
- metadata-only workflow graph export
- step retries with a fixed delay policy
- validation for workflow definitions and step signatures
- structured workflow and step result objects
- optional `raise_on_failure=True` behavior

This means a developer can already define a typed state object, write a small
workflow class around it, run the workflow, and inspect both the final state and
the detailed execution results afterward.

## Current runtime model

The implemented runtime follows a simple model:

1. A workflow class is defined with `@workflow`.
2. Step methods are declared with `@step`.
3. A state object is passed into `workflow_instance.run(state)`.
4. Steps execute in order unless a routed step chooses a later step.
5. Each step can mutate shared workflow state.
6. Approval handlers are called before approval-gated steps run.
7. Retry behavior is applied when configured.
8. Route decisions and skipped steps are recorded when branching is used.
9. The runtime returns a structured `WorkflowResult`.

Separately, users can export the declared workflow structure as a Mermaid graph
without running the workflow.

In practice, this makes the current SDK especially suitable for workflows such
as:

- refund handling
- support ticket triage
- content review and moderation decisions
- branching approval or denial workflows
- internal assistant workflows with a small number of ordered stages

## Public API status

The top-level `agentflow` package currently exposes the main MVP surface area:

- `workflow`
- `step`
- `WorkflowResult`
- `StepResult`
- `RetryPolicy`
- `END`
- `ApprovalRequest`
- `ApprovalDecision`
- `RouteDecision`
- `WorkflowGraph`
- `WorkflowGraphNode`
- `WorkflowGraphEdge`
- `export_workflow_graph`
- `ApprovalRequiredError`
- `RouteResolutionError`
- framework-specific exception types

This public API is enough to author and run the examples currently included in
the repository. It is intentionally small and focused.

## What results you can inspect

The current runtime already returns useful structured execution data.

A workflow caller can inspect:

- overall workflow status
- the final workflow state object
- per-step outputs
- per-step errors
- per-step attempt counts
- route decisions and skipped-step reasons for branching workflows
- approval decisions for approval-gated steps
- timing information for workflow and step execution
- workflow graph nodes and edges before execution

This gives the project immediate practical value even without dashboards or
external tracing integrations, because the caller can already understand what
happened during execution from the returned result object alone.

## Validation and safety currently implemented

The MVP includes a validation layer that protects the authoring model from
common mistakes.

Today, the project validates things such as:

- workflow definitions
- reserved method naming rules
- route targets and route direction
- approval metadata
- step signature expectations
- invalid step metadata or conflicting declarations

This is important because the SDK is trying to provide a lightweight developer
experience without becoming "just conventions and hope."

## Examples currently included

The repository includes runnable example workflows under `examples/`:

- `refund_workflow.py`
- `support_triage.py`
- `content_review.py`
- `branching_refund_workflow.py`
- `approval_refund_workflow.py`
- `graph_export.py`

These examples demonstrate the implemented runtime rather than imaginary future
features. Together they show:

- linear execution
- state mutation across steps
- context-aware workflow logic
- retry behavior on transient failures
- route-based branching with explicit terminal paths
- human approval callbacks with approved and denied decisions
- graph export with Mermaid rendering
- inspection of final results and step-level details

## Current repository maturity

The repository currently contains more than just the runtime code.

It also includes:

- the SDK implementation under `src/agentflow/`
- behavior-focused tests under `tests/`
- runnable usage examples under `examples/`
- CI and release validation under `.github/workflows/`
- public documentation under `docs/`

So the project has already moved beyond a prototype script bundle. It now has
the shape of a real early-stage Python SDK repository.

## What is not implemented yet

The current MVP does not yet include:

- async execution
- persistent approval pause/resume
- worker backends
- dashboards
- interactive visual editors
- graph execution
- framework adapters such as LangGraph integration

These are future extensions, not hidden or partially implemented features.

## Best way to think about the project right now

Agent Workflow Kit is currently a focused MVP for stateful, decorator-based
workflow orchestration in Python.

It is already useful for real small-scale agent workflows, but it is still
early in scope. The current strength of the project is clarity:

- a small public API
- a simple execution model
- typed state plus ordered steps
- branching, retries, validation, and structured results built into the runtime
- graph export for inspecting workflow structure before execution

That is the current status of the project today.
