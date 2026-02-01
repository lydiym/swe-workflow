"""Abstract base classes for command handlers to replace conditional logic with polymorphism."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from argparse import Namespace


class CommandHandler(ABC):
    """Abstract base class for command-specific handlers."""
    
    @property
    @abstractmethod
    def command_name(self) -> str:
        """Return the name of the command this handler manages."""
        pass

    @abstractmethod
    def execute(self, args: Namespace) -> None:
        """Execute the command with the given arguments."""
        pass


class CommandHandlerRegistry:
    """Registry to manage command handlers and provide lookup functionality."""
    
    def __init__(self):
        self._handlers: dict[str, CommandHandler] = {}
    
    def register(self, handler: CommandHandler) -> None:
        """Register a command handler."""
        self._handlers[handler.command_name] = handler
    
    def get_handler(self, command_name: str) -> CommandHandler | None:
        """Get a handler for the specified command name."""
        return self._handlers.get(command_name)
    
    def execute_command(self, command_name: str, args: Namespace) -> bool:
        """Execute a command by name, returning True if found and executed."""
        handler = self.get_handler(command_name)
        if handler:
            handler.execute(args)
            return True
        return False


# Global registry instance
registry = CommandHandlerRegistry()