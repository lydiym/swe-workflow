"""Concrete implementations of tool handlers for file operations."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from deepagents.backends.utils import perform_string_replacement

from swe_workflow.file_ops import ApprovalPreview, _count_lines, _safe_read, compute_unified_diff, format_display_path, resolve_physical_path
from swe_workflow.tool_handlers.base import ToolHandler

if TYPE_CHECKING:
    pass


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
        return path_str


class WriteFileHandler(ToolHandler):
    """Handler for write_file tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "write_file"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None) -> ApprovalPreview | None:
        """Build an approval preview for write_file operations."""
        path_str = str(args.get("file_path") or args.get("path") or "")
        display_path = format_display_path(path_str)
        physical_path = resolve_physical_path(path_str, assistant_id)
        
        content = str(args.get("content", ""))
        before = _safe_read(physical_path) if physical_path and physical_path.exists() else ""
        after = content
        diff = compute_unified_diff(before or "", after, display_path, max_lines=100)
        additions = 0
        if diff:
            additions = sum(
                1
                for line in diff.splitlines()
                if line.startswith("+") and not line.startswith("+++")
            )
        total_lines = _count_lines(after)
        details = [
            f"File: {path_str}",
            "Action: Create new file" + (" (overwrites existing content)" if before else ""),
            f"Lines to write: {additions or total_lines}",
        ]
        return ApprovalPreview(
            title=f"Write {display_path}",
            details=details,
            diff=diff,
            diff_title=f"Diff {display_path}",
        )

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the write_file tool call for display purposes."""
        # File operations: show the primary file path argument (file_path or path)
        path_value = tool_args.get("file_path")
        if path_value is None:
            path_value = tool_args.get("path")
        if path_value is not None:
            path = _abbreviate_path(str(path_value))
            return f"{self.tool_name}({path})"
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"


class EditFileHandler(ToolHandler):
    """Handler for edit_file tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "edit_file"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None) -> ApprovalPreview | None:
        """Build an approval preview for edit_file operations."""
        path_str = str(args.get("file_path") or args.get("path") or "")
        display_path = format_display_path(path_str)
        physical_path = resolve_physical_path(path_str, assistant_id)
        
        if physical_path is None:
            return ApprovalPreview(
                title=f"Update {display_path}",
                details=[f"File: {path_str}", "Action: Replace text"],
                error="Unable to resolve file path.",
            )
        before = _safe_read(physical_path)
        if before is None:
            return ApprovalPreview(
                title=f"Update {display_path}",
                details=[f"File: {path_str}", "Action: Replace text"],
                error="Unable to read current file contents.",
            )
        old_string = str(args.get("old_string", ""))
        new_string = str(args.get("new_string", ""))
        replace_all = bool(args.get("replace_all", False))
        replacement = perform_string_replacement(before, old_string, new_string, replace_all)
        if isinstance(replacement, str):
            return ApprovalPreview(
                title=f"Update {display_path}",
                details=[f"File: {path_str}", "Action: Replace text"],
                error=replacement,
            )
        after, occurrences = replacement
        diff = compute_unified_diff(before, after, display_path, max_lines=None)
        additions = 0
        deletions = 0
        if diff:
            additions = sum(
                1
                for line in diff.splitlines()
                if line.startswith("+") and not line.startswith("+++")
            )
            deletions = sum(
                1
                for line in diff.splitlines()
                if line.startswith("-") and not line.startswith("---")
            )
        details = [
            f"File: {path_str}",
            f"Action: Replace text ({'all occurrences' if replace_all else 'single occurrence'})",
            f"Occurrences matched: {occurrences}",
            f"Lines changed: +{additions} / -{deletions}",
        ]
        return ApprovalPreview(
            title=f"Update {display_path}",
            details=details,
            diff=diff,
            diff_title=f"Diff {display_path}",
        )

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the edit_file tool call for display purposes."""
        # File operations: show the primary file path argument (file_path or path)
        path_value = tool_args.get("file_path")
        if path_value is None:
            path_value = tool_args.get("path")
        if path_value is not None:
            path = _abbreviate_path(str(path_value))
            return f"{self.tool_name}({path})"
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"


class ReadFileHandler(ToolHandler):
    """Handler for read_file tool operations."""
    
    @property
    def tool_name(self) -> str:
        return "read_file"

    def build_approval_preview(self, args: dict[str, Any], assistant_id: str | None) -> ApprovalPreview | None:
        """Build an approval preview for read_file operations."""
        # Read operations typically don't need approval previews
        return None

    def format_display(self, tool_args: dict[str, Any]) -> str:
        """Format the read_file tool call for display purposes."""
        # File operations: show the primary file path argument (file_path or path)
        path_value = tool_args.get("file_path")
        if path_value is None:
            path_value = tool_args.get("path")
        if path_value is not None:
            path = _abbreviate_path(str(path_value))
            return f"{self.tool_name}({path})"
        # Fallback: generic formatting for unknown tools
        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        return f"{self.tool_name}({args_str})"