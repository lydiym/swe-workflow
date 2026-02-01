"""Concrete implementations of tool handlers for general tools."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from swe_workflow.tool_handlers.base import ToolHandler

if TYPE_CHECKING:
    pass


def truncate_value(value: str, max_length: int = 60) -> str:
    """Truncate a string value if it exceeds max_length."""
    if len(value) > max_length:
        return value[:max_length] + "..."
    return value


def _abbreviate_path(path_str: str, max_length: int = 60) -> str:
    """Abbreviate a file path intelligently - show basename or relative path."""
    try:
        path = Path(path_str)

        # If it's just a filename (no directory parts), return as-is
        if len(path.parts) == 1:
            return path_str

        # Try to get relative path from current working directory
        try:
            rel_path = path.relative_to(Path.cwd())
            rel_str = str(rel_path)
            # Use relative if it's shorter and not too long
            if len(rel_str) < len(path_str) and len(rel_str) <= max_length:
                return rel_str
        except (ValueError, Exception):
            pass

        # If absolute path is reasonable length, use it
        if len(path_str) <= max_length:
            return path_str

        # Otherwise, just show basename (filename only)
        return path.name
    except Exception:
        # Fallback to original string if any error
        return truncate_value(path_str, max_length)


class ShellHandler(ToolHandler):
    """Handler for shell tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "shell"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None):
        """Shell operations typically don't need approval previews."""
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the shell tool call for display purposes."""
        # Shell: show the command being executed
        if "command" in tool_args:
            command = str(tool_args["command"])
            command = truncate_value(command, 120)
            return f'{self.tool_name}("{command}")'
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"


class GrepHandler(ToolHandler):
    """Handler for grep tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "grep"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None):
        """Grep operations typically don't need approval previews."""
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the grep tool call for display purposes."""
        # Grep: show the search pattern
        if "pattern" in tool_args:
            pattern = str(tool_args["pattern"])
            pattern = truncate_value(pattern, 70)
            return f'{self.tool_name}("{pattern}")'
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"


class LsHandler(ToolHandler):
    """Handler for ls tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "ls"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None):
        """Ls operations typically don't need approval previews."""
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the ls tool call for display purposes."""
        # ls: show directory, or empty if current directory
        if tool_args.get("path"):
            path = _abbreviate_path(str(tool_args["path"]))
            return f"{self.tool_name}({path})"
        return f"{self.tool_name}()"


class GlobHandler(ToolHandler):
    """Handler for glob tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "glob"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None):
        """Glob operations typically don't need approval previews."""
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the glob tool call for display purposes."""
        # Glob: show the pattern
        if "pattern" in tool_args:
            pattern = str(tool_args["pattern"])
            pattern = truncate_value(pattern, 80)
            return f'{self.tool_name}("{pattern}")'
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"


class HttpRequestHandler(ToolHandler):
    """Handler for http_request tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "http_request"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None):
        """HTTP request operations typically don't need approval previews."""
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the http_request tool call for display purposes."""
        # HTTP: show method and URL
        parts = []
        if "method" in tool_args:
            parts.append(str(tool_args["method"]).upper())
        if "url" in tool_args:
            url = str(tool_args["url"])
            url = truncate_value(url, 80)
            parts.append(url)
        if parts:
            return f"{self.tool_name}({' '.join(parts)})"
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"


class FetchUrlHandler(ToolHandler):
    """Handler for fetch_url tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "fetch_url"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None):
        """Fetch URL operations typically don't need approval previews."""
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the fetch_url tool call for display purposes."""
        # Fetch URL: show the URL being fetched
        if "url" in tool_args:
            url = str(tool_args["url"])
            url = truncate_value(url, 80)
            return f'{self.tool_name}("{url}")'
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"


class TaskHandler(ToolHandler):
    """Handler for task tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "task"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None):
        """Task operations typically don't need approval previews."""
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the task tool call for display purposes."""
        # Task: show the task description
        if "description" in tool_args:
            desc = str(tool_args["description"])
            desc = truncate_value(desc, 100)
            return f'{self.tool_name}("{desc}")'
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"


class WriteTodosHandler(ToolHandler):
    """Handler for write_todos tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "write_todos"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None):
        """Write todos operations typically don't need approval previews."""
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the write_todos tool call for display purposes."""
        # Todos: show count of items
        if "todos" in tool_args and isinstance(tool_args["todos"], list):
            count = len(tool_args["todos"])
            return f"{self.tool_name}({count} items)"
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"