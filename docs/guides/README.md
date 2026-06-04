# Guides

This folder contains practical usage guides for Agent Workflow Kit.

If `docs/architecture/` explains how the SDK is built, `docs/guides/`
explains how to use it.

## Start here

If you are new to the project, read these guides in this order:

1. [first-workflow.md](first-workflow.md)
2. [retries-and-failures.md](retries-and-failures.md)
3. [inspecting-results.md](inspecting-results.md)
4. [branching-workflows.md](branching-workflows.md)
5. [human-approval.md](human-approval.md)
6. [workflow-hooks.md](workflow-hooks.md)
7. [workflow-composition.md](workflow-composition.md)
8. [workflow-graphs.md](workflow-graphs.md)

## What these guides cover

- how to write and run your first workflow
- how shared state works in practice
- how retry settings affect step execution
- how to handle failure behavior
- how to inspect `WorkflowResult` and `StepResult`
- how to route workflows into conditional paths
- how to gate selected steps with synchronous approval callbacks
- how to observe execution with synchronous lifecycle hooks
- how to run child workflows from context-aware parent steps
- how to export workflow metadata as Mermaid diagrams

## What these guides do not cover

These guides do not try to explain the deeper runtime internals in detail.

For that, use:

- [../architecture/overview.md](../architecture/overview.md)
- [../architecture/runtime.md](../architecture/runtime.md)
- [../architecture/api.md](../architecture/api.md)
