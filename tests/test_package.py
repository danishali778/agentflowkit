"""Smoke tests for the package foundation."""

import agentflow


def test_package_exposes_version() -> None:
    """The foundation package should expose a version string."""
    assert agentflow.__version__ == "0.1.0"
