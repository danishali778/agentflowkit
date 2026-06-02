# Current Project Status

## Summary

Agent Workflow Kit is currently a working MVP Python SDK for building linear
agent workflows with plain Python classes and decorators.

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
4. Steps execute in order.
5. Each step can mutate shared workflow state.
6. Retry behavior is applied when configured.
7. The runtime returns a structured `WorkflowResult`.

In practice, this makes the current SDK especially suitable for workflows such
as:

- refund handling
- support ticket triage
- content review and moderation decisions
- internal assistant workflows with a small number of ordered stages

## Public API status

The top-level `agentflow` package currently exposes the main MVP surface area:

- `workflow`
- `step`
- `WorkflowResult`
- `StepResult`
- `RetryPolicy`
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
- timing information for workflow and step execution

This gives the project immediate practical value even without dashboards or
external tracing integrations, because the caller can already understand what
happened during execution from the returned result object alone.

## Validation and safety currently implemented

The MVP includes a validation layer that protects the authoring model from
common mistakes.

Today, the project validates things such as:

- workflow definitions
- reserved method naming rules
- step signature expectations
- invalid step metadata or conflicting declarations

This is important because the SDK is trying to provide a lightweight developer
experience without becoming “just conventions and hope.”

## Examples currently included

The repository includes runnable example workflows under `examples/`:

- `refund_workflow.py`
- `support_triage.py`
- `content_review.py`

These examples demonstrate the implemented runtime rather than imaginary future
features. Together they show:

- linear execution
- state mutation across steps
- context-aware workflow logic
- retry behavior on transient failures
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

- branching or conditional routing
- human approval steps
- async execution
- worker backends
- dashboards
- workflow visualization
- framework adapters such as LangGraph integration

These are future extensions, not hidden or partially implemented features.

## Best way to think about the project right now

Agent Workflow Kit is currently a focused MVP for linear, stateful,
decorator-based workflow orchestration in Python.

It is already useful for real small-scale agent workflows, but it is still
early in scope. The current strength of the project is clarity:

- a small public API
- a simple execution model
- typed state plus ordered steps
- retries, validation, and structured results built into the runtime

That is the current status of the project today.
