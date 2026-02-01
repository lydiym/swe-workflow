"""Registry initialization for all command handlers."""

from .base import registry
from .skills_commands import (
    SkillsListCommandHandler,
    SkillsCreateCommandHandler,
    SkillsInfoCommandHandler,
)
from .main_commands import (
    HelpCommandHandler,
    ListCommandHandler,
    ResetCommandHandler,
    SkillsCommandHandler,
    ThreadsCommandHandler,
)
from .threads_commands import (
    ThreadsListCommandHandler,
    ThreadsDeleteCommandHandler,
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


__all__ = ['registry']