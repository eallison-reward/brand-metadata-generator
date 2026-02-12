"""Placeholder test to ensure CI passes until real tests are implemented."""

import pytest


def test_placeholder():
    """Placeholder test that always passes."""
    assert True


def test_python_version():
    """Verify Python version is 3.12 or higher."""
    import sys
    assert sys.version_info >= (3, 12), f"Python 3.12+ required, got {sys.version_info}"
