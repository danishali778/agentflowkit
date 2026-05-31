# Agent Workflow Kit

Agent Workflow Kit is an open-source Python SDK for building agent workflows with plain
Python classes, step decorators, shared state, and reliable execution primitives.

## Status

The project is in its foundation phase. The repository scaffolding, design docs, and CI
strategy are being established before the core runtime is implemented.

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

## Planned developer experience

```python
from agentflow import step, workflow


@workflow
class RefundWorkflow:
    @step
    def check_order(self):
        ...

    @step
    def verify_policy(self):
        ...

    @step
    def generate_response(self):
        ...
```

## Repository structure

The repository uses a `src/` layout and keeps design decisions in `docs/`.

- `docs/` contains architecture, API, startup, scaling, and workflow guidance.
- `src/agentflow/` will contain the SDK implementation.
- `tests/` contains behavior-focused test coverage.
- `.github/workflows/` contains CI and release automation.

## Development

The project targets Python `3.11+`.

### Install development tooling

```bash
pip install -e .[dev]
```

### Run checks

```bash
ruff check .
pytest
```

## Documentation

Start with the docs index:

- [docs/README.md](docs/README.md)

The current source of truth for implementation direction lives in:

- `docs/00-project-definition.md`
- `docs/01-mvp-architecture.md`
- `docs/02-python-api.md`
- `docs/03-package-structure.md`

## Roadmap

The initial build will focus on the documented MVP before any advanced features such as:

- branching
- human approval steps
- adapters
- dashboards
- worker systems

Those remain future work by design.
