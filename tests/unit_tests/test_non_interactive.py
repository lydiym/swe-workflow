"""Tests for non-interactive mode functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from swe_workflow.non_interactive import run_non_interactive_with_resume, execute_task_non_interactive


@pytest.mark.asyncio
async def test_execute_task_non_interactive_returns_bool():
    """Test that execute_task_non_interactive returns a boolean value."""
    # Mock required parameters
    mock_agent = AsyncMock()
    mock_agent.astream = AsyncMock()
    mock_agent.astream.return_value = []
    
    # Call the function
    result = await execute_task_non_interactive(
        user_input="test task",
        agent=mock_agent,
        assistant_id="test_agent",
        thread_id="test_thread"
    )
    
    # Verify the return type
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_run_non_interactive_with_resume_returns_int():
    """Test that run_non_interactive_with_resume returns an integer exit code."""
    with patch('swe_workflow.non_interactive.create_model') as mock_create_model, \
         patch('swe_workflow.non_interactive.get_checkpointer') as mock_get_checkpointer, \
         patch('swe_workflow.non_interactive.create_cli_agent') as mock_create_agent, \
         patch('swe_workflow.non_interactive.generate_thread_id', return_value="test_thread"), \
         patch('swe_workflow.non_interactive.execute_task_non_interactive', return_value=True):
        
        # Mock return values
        mock_create_model.return_value = "test_model"
        mock_checkpointer = AsyncMock()
        mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
        mock_checkpointer.__aexit__ = AsyncMock(return_value=None)
        mock_get_checkpointer.return_value = mock_checkpointer
        
        mock_agent = MagicMock()
        mock_backend = MagicMock()
        mock_create_agent.return_value = (mock_agent, mock_backend)
        
        # Call the function
        result = await run_non_interactive_with_resume(
            task="test task",
            assistant_id="test_agent"
        )
        
        # Verify the return type
        assert isinstance(result, int)
        assert result == 0  # Success exit code


@pytest.mark.asyncio
async def test_run_non_interactive_with_resume_error_handling():
    """Test that run_non_interactive_with_resume handles errors properly."""
    with patch('swe_workflow.non_interactive.create_model') as mock_create_model, \
         patch('swe_workflow.non_interactive.get_checkpointer') as mock_get_checkpointer, \
         patch('swe_workflow.non_interactive.create_cli_agent') as mock_create_agent, \
         patch('swe_workflow.non_interactive.generate_thread_id', return_value="test_thread"):
        
        # Mock return values
        mock_create_model.return_value = "test_model"
        mock_checkpointer = AsyncMock()
        mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
        mock_checkpointer.__aexit__ = AsyncMock(return_value=None)
        mock_get_checkpointer.return_value = mock_checkpointer
        
        # Make create_cli_agent raise an exception
        mock_create_agent.side_effect = Exception("Test error")
        
        # Call the function
        result = await run_non_interactive_with_resume(
            task="test task",
            assistant_id="test_agent"
        )
        
        # Verify the return type and value
        assert isinstance(result, int)
        assert result == 1  # Error exit code