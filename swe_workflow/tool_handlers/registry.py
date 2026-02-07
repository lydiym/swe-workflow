"""Registry initialization for all tool handlers."""

from .base import registry
from .file_operations import EditFileHandler, ReadFileHandler, WriteFileHandler
from .general_tools import (
    FetchUrlHandler,
    GlobHandler,
    GrepHandler,
    HttpRequestHandler,
    LsHandler,
    ShellHandler,
    TaskHandler,
    WriteTodosHandler,
)


def initialize_registry():
    """Initialize the registry with all available tool handlers."""
    handlers = [
        WriteFileHandler(),
        EditFileHandler(),
        ReadFileHandler(),
        ShellHandler(),
        GrepHandler(),
        LsHandler(),
        GlobHandler(),
        HttpRequestHandler(),
        FetchUrlHandler(),
        TaskHandler(),
        WriteTodosHandler(),
    ]

    for handler in handlers:
        registry.register(handler)


# Initialize the registry when this module is imported
initialize_registry()


__all__ = ["registry"]
