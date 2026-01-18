"""Test importing files."""


def test_imports() -> None:
    """Test importing swe_workflow modules."""
    from swe_workflow import (
        agent,  # noqa: F401
        integrations,  # noqa: F401
    )
    from swe_workflow.main import cli_main  # noqa: F401
