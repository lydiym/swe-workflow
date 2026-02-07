"""Concrete implementations of command handlers for threads subcommands."""

from __future__ import annotations

import asyncio
from argparse import Namespace

from swe_workflow.command_handlers.base import CommandHandler
from swe_workflow.sessions import delete_thread_command, list_threads_command


class ThreadsListCommandHandler(CommandHandler):
    """Handler for the 'threads list' command."""

    @property
    def command_name(self) -> str:
        return "threads_list"

    def execute(self, args: Namespace) -> None:
        """Execute the threads list command."""
        asyncio.run(
            list_threads_command(
                agent_name=getattr(args, "agent", None),
                limit=getattr(args, "limit", 20),
            )
        )


class ThreadsDeleteCommandHandler(CommandHandler):
    """Handler for the 'threads delete' command."""

    @property
    def command_name(self) -> str:
        return "threads_delete"

    def execute(self, args: Namespace) -> None:
        """Execute the threads delete command."""
        asyncio.run(delete_thread_command(args.thread_id))
