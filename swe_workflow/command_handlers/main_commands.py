"""Concrete implementations of command handlers for main commands."""

from __future__ import annotations

import asyncio
from argparse import Namespace

from swe_workflow.command_handlers.base import CommandHandler


class HelpCommandHandler(CommandHandler):
    """Handler for the 'help' command."""
    
    @property
    def command_name(self) -> str:
        return "help"

    def execute(self, args: Namespace) -> None:
        """Execute the help command."""
        from swe_workflow.ui import show_help
        show_help()


class ListCommandHandler(CommandHandler):
    """Handler for the 'list' command."""
    
    @property
    def command_name(self) -> str:
        return "list"

    def execute(self, args: Namespace) -> None:
        """Execute the list command."""
        from swe_workflow.agent import list_agents
        list_agents()


class ResetCommandHandler(CommandHandler):
    """Handler for the 'reset' command."""
    
    @property
    def command_name(self) -> str:
        return "reset"

    def execute(self, args: Namespace) -> None:
        """Execute the reset command."""
        from swe_workflow.agent import reset_agent
        reset_agent(args.agent, getattr(args, 'source_agent', None))


class SkillsCommandHandler(CommandHandler):
    """Handler for the 'skills' command."""
    
    @property
    def command_name(self) -> str:
        return "skills"

    def execute(self, args: Namespace) -> None:
        """Execute the skills command."""
        from swe_workflow.skills.commands import execute_skills_command
        execute_skills_command(args)


class ThreadsCommandHandler(CommandHandler):
    """Handler for the 'threads' command that delegates to subcommand handlers."""
    
    def __init__(self):
        """Initialize with subcommand handlers."""
        from .registry import registry
        self._list_handler = registry.get_handler("threads_list")
        self._delete_handler = registry.get_handler("threads_delete")
    
    @property
    def command_name(self) -> str:
        return "threads"

    def execute(self, args: Namespace) -> None:
        """Execute the threads command by delegating to appropriate subcommand handler."""
        from ..config import console
        threads_command = getattr(args, 'threads_command', None)
        
        if threads_command == "list":
            if self._list_handler:
                self._list_handler.execute(args)
            else:
                console.print("[yellow]Error: threads list command handler not found[/yellow]")
        elif threads_command == "delete":
            if self._delete_handler:
                self._delete_handler.execute(args)
            else:
                console.print("[yellow]Error: threads delete command handler not found[/yellow]")
        else:
            console.print("[yellow]Usage: swe-workflow threads <list|delete>[/yellow]")