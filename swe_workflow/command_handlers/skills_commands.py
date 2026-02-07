"""Concrete implementations of command handlers for skills commands."""

from __future__ import annotations

from argparse import Namespace

from swe_workflow.command_handlers.base import CommandHandler


class SkillsListCommandHandler(CommandHandler):
    """Handler for the 'list' skills command."""

    @property
    def command_name(self) -> str:
        return "list"

    def execute(self, args: Namespace) -> None:
        """Execute the skills list command."""
        from swe_workflow.skills.commands import _list

        _list(agent=args.agent, project=getattr(args, "project", False))


class SkillsCreateCommandHandler(CommandHandler):
    """Handler for the 'create' skills command."""

    @property
    def command_name(self) -> str:
        return "create"

    def execute(self, args: Namespace) -> None:
        """Execute the skills create command."""
        from swe_workflow.skills.commands import _create

        _create(args.name, agent=args.agent, project=getattr(args, "project", False))


class SkillsInfoCommandHandler(CommandHandler):
    """Handler for the 'info' skills command."""

    @property
    def command_name(self) -> str:
        return "info"

    def execute(self, args: Namespace) -> None:
        """Execute the skills info command."""
        from swe_workflow.skills.commands import _info

        _info(args.name, agent=args.agent, project=getattr(args, "project", False))
