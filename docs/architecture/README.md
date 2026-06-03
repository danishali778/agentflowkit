# Architecture Docs

This folder explains the current architecture of Agent Workflow Kit.

The focus here is the architecture that is **implemented today**, not the full
long-term vision of the project.

If you are new to the codebase, read these files in this order:

1. [overview.md](overview.md)
2. [runtime.md](runtime.md)
3. [api.md](api.md)

## What these docs cover

- the main runtime building blocks
- how a workflow moves from definition to execution
- how lifecycle hooks observe execution
- how workflow metadata can be exported as a graph
- how state, validation, retries, and results fit together
- what the current public API exposes
- what the current implementation does and does not do

## What these docs do not cover

These docs do not try to define future platform ideas such as:

- dashboards
- distributed workers
- graph editors
- hosted orchestration services

Those may come later, but this folder is meant to describe the architecture the
repository actually contains right now.
