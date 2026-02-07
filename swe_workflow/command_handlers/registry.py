"""Registry initialization for all command handlers."""

from .base import registry
from .main_commands import (
    HelpCommandHandler,
    ListCommandHandler,
    ResetCommandHandler,
    SkillsCommandHandler,
    ThreadsCommandHandler,
)
from .skills_commands import (
    SkillsCreateCommandHandler,
    SkillsInfoCommandHandler,
    SkillsListCommandHandler,
)
from .threads_commands import (
    ThreadsDeleteCommandHandler,
    ThreadsListCommandHandler,
)


def initialize_registry():
    """Initialize the registry with all available command handlers."""
    handlers = [
        SkillsListCommandHandler(),
        SkillsCreateCommandHandler(),
        SkillsInfoCommandHandler(),
        HelpCommandHandler(),
        ListCommandHandler(),
        ResetCommandHandler(),
        SkillsCommandHandler(),
        ThreadsCommandHandler(),
        ThreadsListCommandHandler(),
        ThreadsDeleteCommandHandler(),
    ]

    for handler in handlers:
        registry.register(handler)


# Initialize the registry when this module is imported
initialize_registry()


__all__ = ["registry"]
