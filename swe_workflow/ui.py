"""UI rendering and display utilities for the CLI."""

import json
from pathlib import Path
from typing import Any

from .config import COLORS, DEEP_AGENTS_ASCII, MAX_ARG_LENGTH, console


def truncate_value(value: str, max_length: int = MAX_ARG_LENGTH) -> str:
    """Truncate a string value if it exceeds max_length."""
    if len(value) > max_length:
        return value[:max_length] + "..."
    return value


def format_tool_display(tool_name: str, tool_args: dict) -> str:
    """Format tool calls for display with tool-specific smart formatting.

    Shows the most relevant information for each tool type rather than all arguments.

    Args:
        tool_name: Name of the tool being called
        tool_args: Dictionary of tool arguments

    Returns:
        Formatted string for display (e.g., "read_file(config.py)")

    Examples:
        read_file(path="/long/path/file.py") → "read_file(file.py)"
        shell(command="pip install foo") → 'shell("pip install foo")'
    """
    # Use the handler registry to find the appropriate handler for the tool
    # Import here to avoid circular import issues
    from .tool_handlers.registry import registry
    handler = registry.get_handler(tool_name)
    if handler:
        return handler.format_display(tool_args)
    
    # Fallback: generic formatting for unknown tools
    # Show all arguments in key=value format
    args_str = ", ".join(f"{k}={truncate_value(str(v), 50)}" for k, v in tool_args.items())
    return f"{tool_name}({args_str})"


def format_tool_message_content(content: Any) -> str:
    """Convert ToolMessage content into a printable string."""
    if content is None:
        return ""
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            else:
                try:
                    parts.append(json.dumps(item))
                except Exception:
                    parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def show_help() -> None:
    """Show help information."""
    console.print()
    console.print(DEEP_AGENTS_ASCII, style=f"bold {COLORS['primary']}")
    console.print()

    console.print("[bold]Usage:[/bold]", style=COLORS["primary"])
    console.print("  swe-workflow [OPTIONS]                           Start interactive session")
    console.print("  swe-workflow list                                List all available agents")
    console.print(
        "  swe-workflow reset --agent AGENT                 Reset agent to default prompt"
    )
    console.print(
        "  swe-workflow reset --agent AGENT --target SOURCE Reset agent to copy of another agent"
    )
    console.print("  swe-workflow help                                Show this help message")
    console.print("  swe-workflow --version                           Show swe-workflow version")
    console.print()

    console.print("[bold]Options:[/bold]", style=COLORS["primary"])
    console.print("  --agent NAME                  Agent identifier (default: agent)")
    console.print(
        "  --model MODEL                 Model to use (e.g., claude-sonnet-4-5-20250929, gpt-4o)"
    )
    console.print("  --auto-approve                Auto-approve tool usage without prompting")
    console.print("  --non-interactive, --batch    Run in non-interactive mode without UI")
    console.print("  --task TASK                   Task to execute in non-interactive mode")
    console.print("  -r, --resume [ID]             Resume thread: -r for most recent, -r <ID> for specific")
    console.print()
    console.print()

    console.print("[bold]Examples:[/bold]", style=COLORS["primary"])
    console.print(
        "  swe-workflow                              # Start with default agent",
        style=COLORS["dim"],
    )
    console.print(
        "  swe-workflow --agent mybot                # Start with agent named 'mybot'",
        style=COLORS["dim"],
    )
    console.print(
        "  swe-workflow --model gpt-4o               # Use specific model (auto-detects provider)",
        style=COLORS["dim"],
    )
    console.print(
        "  swe-workflow -r                           # Resume most recent session",
        style=COLORS["dim"],
    )
    console.print(
        "  swe-workflow -r abc123                    # Resume specific thread",
        style=COLORS["dim"],
    )
    console.print(
        "  swe-workflow --auto-approve               # Start with auto-approve enabled",
        style=COLORS["dim"],
    )
    console.print(
        "  swe-workflow --non-interactive --task \"Do something\"  # Run without UI",
        style=COLORS["dim"],
    )
    console.print()

    console.print("[bold]Thread Management:[/bold]", style=COLORS["primary"])
    console.print(
        "  swe-workflow threads list                 # List all sessions", style=COLORS["dim"]
    )
    console.print(
        "  swe-workflow threads delete <ID>          # Delete a session", style=COLORS["dim"]
    )
    console.print()

    console.print("[bold]Interactive Features:[/bold]", style=COLORS["primary"])
    console.print("  Enter           Submit your message", style=COLORS["dim"])
    console.print("  Ctrl+J          Insert newline", style=COLORS["dim"])
    console.print("  Shift+Tab       Toggle auto-approve mode", style=COLORS["dim"])
    console.print("  @filename       Auto-complete files and inject content", style=COLORS["dim"])
    console.print("  /command        Slash commands (/help, /clear, /quit)", style=COLORS["dim"])
    console.print("  !command        Run bash commands directly", style=COLORS["dim"])
    console.print()
