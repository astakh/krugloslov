"""Pytest configuration and fixtures."""

from __future__ import annotations

import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--database-url",
        action="store",
        default=None,
        help="Database URL for integration tests",
    )
