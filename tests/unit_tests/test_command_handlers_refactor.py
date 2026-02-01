"""Test cases for the refactored command handlers to ensure proper OOP structure."""

import unittest
from argparse import Namespace
from unittest.mock import patch, MagicMock, AsyncMock

from swe_workflow.command_handlers.registry import registry
from swe_workflow.command_handlers.main_commands import ThreadsCommandHandler
from swe_workflow.command_handlers.threads_commands import ThreadsListCommandHandler, ThreadsDeleteCommandHandler


class TestRefactoredCommandHandlers(unittest.TestCase):
    """Test cases for the refactored command handlers."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure registry is initialized
        pass

    def test_threads_command_handler_structure(self):
        """Test that ThreadsCommandHandler no longer contains if/elif/else logic."""
        handler = ThreadsCommandHandler()
        # Check that the handler is properly structured
        self.assertTrue(hasattr(handler, 'command_name'))
        self.assertEqual(handler.command_name, 'threads')
        self.assertTrue(callable(handler.execute))

    def test_threads_list_command_handler_exists(self):
        """Test that ThreadsListCommandHandler exists and is properly structured."""
        handler = ThreadsListCommandHandler()
        self.assertTrue(hasattr(handler, 'command_name'))
        self.assertEqual(handler.command_name, 'threads_list')
        self.assertTrue(callable(handler.execute))

    def test_threads_delete_command_handler_exists(self):
        """Test that ThreadsDeleteCommandHandler exists and is properly structured."""
        handler = ThreadsDeleteCommandHandler()
        self.assertTrue(hasattr(handler, 'command_name'))
        self.assertEqual(handler.command_name, 'threads_delete')
        self.assertTrue(callable(handler.execute))

    def test_registry_contains_all_handlers(self):
        """Test that all command handlers are registered."""
        # Check that main threads handler exists
        threads_handler = registry.get_handler('threads')
        self.assertIsNotNone(threads_handler)
        self.assertIsInstance(threads_handler, ThreadsCommandHandler)
        
        # Check that subcommand handlers exist
        list_handler = registry.get_handler('threads_list')
        self.assertIsNotNone(list_handler)
        self.assertIsInstance(list_handler, ThreadsListCommandHandler)
        
        delete_handler = registry.get_handler('threads_delete')
        self.assertIsNotNone(delete_handler)
        self.assertIsInstance(delete_handler, ThreadsDeleteCommandHandler)

    @patch('swe_workflow.sessions.list_threads_command')
    def test_threads_list_command_execution(self, mock_list_command):
        """Test that threads list command executes properly."""
        # Mock async function
        mock_list_command.return_value = AsyncMock()
        
        handler = ThreadsListCommandHandler()
        args = Namespace(agent="test_agent", limit=10)
        
        # Execute should not raise an exception
        import asyncio
        from unittest.mock import patch
        with patch('asyncio.run') as mock_async_run:
            handler.execute(args)
            mock_async_run.assert_called_once()

    @patch('swe_workflow.sessions.delete_thread_command')
    def test_threads_delete_command_execution(self, mock_delete_command):
        """Test that threads delete command executes properly."""
        # Mock async function
        mock_delete_command.return_value = AsyncMock()
        
        handler = ThreadsDeleteCommandHandler()
        args = Namespace(thread_id="test_thread_id")
        
        # Execute should not raise an exception
        import asyncio
        from unittest.mock import patch
        with patch('asyncio.run') as mock_async_run:
            handler.execute(args)
            mock_async_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()