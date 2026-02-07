"""Abstract base classes for tool handlers to replace conditional logic with polymorphism."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from swe_workflow.file_ops import ApprovalPreview


class ToolHandler(ABC):
    """Abstract base class for tool-specific handlers."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return the name of the tool this handler manages."""

    @abstractmethod
    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None) -> ApprovalPreview | None:
        """Build an approval preview for the tool."""

    @abstractmethod
    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the tool call for display purposes."""


class ToolHandlerRegistry:
    """Registry to manage tool handlers and provide lookup functionality."""

    def __init__(self):
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, handler: ToolHandler) -> None:
        """Register a tool handler."""
        self._handlers[handler.tool_name] = handler

    def get_handler(self, tool_name: str) -> ToolHandler | None:
        """Get a handler for the specified tool name."""
        return self._handlers.get(tool_name)

    def get_all_handler_names(self) -> list[str]:
        """Get all registered handler names."""
        return list(self._handlers.keys())


# Global registry instance
registry = ToolHandlerRegistry()
