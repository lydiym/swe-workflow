"""Content block handling strategies using the Strategy pattern to replace if/elif chains."""

import json
from abc import ABC, abstractmethod
from typing import Any


class ContentBlockHandler(ABC):
    """Abstract base class for content block handling strategies."""

    def __init__(self, next_handler: "ContentBlockHandler" = None):
        self.next_handler = next_handler

    def set_next(self, handler: "ContentBlockHandler") -> "ContentBlockHandler":
        """Set the next handler in the chain."""
        self.next_handler = handler
        return handler

    def handle(self, block: dict[str, Any], tool_call_buffers: dict, print_func: Any = print) -> bool:
        """Handle a content block, returning True if handled, False otherwise."""
        if self.can_handle(block):
            self._handle_specific(block, tool_call_buffers, print_func)
            return True

        if self.next_handler:
            return self.next_handler.handle(block, tool_call_buffers, print_func)

        return False

    @abstractmethod
    def can_handle(self, block: dict[str, Any]) -> bool:
        """Check if this handler can handle the given block."""

    @abstractmethod
    def _handle_specific(self, block: dict[str, Any], tool_call_buffers: dict, print_func: Any) -> None:
        """Handle the block specifically for this handler type."""


class TextBlockHandler(ContentBlockHandler):
    """Handler for text content blocks."""

    def can_handle(self, block: dict[str, Any]) -> bool:
        return block.get("type") == "text"

    def _handle_specific(self, block: dict[str, Any], tool_call_buffers: dict, print_func: Any) -> None:
        text = block.get("text", "")
        if text:
            print_func(text, end="", flush=True)


class ToolCallBlockHandler(ContentBlockHandler):
    """Handler for tool call content blocks."""

    def can_handle(self, block: dict[str, Any]) -> bool:
        return block.get("type") in ("tool_call_chunk", "tool_call")

    def _handle_specific(self, block: dict[str, Any], tool_call_buffers: dict, print_func: Any) -> None:
        chunk_name = block.get("name")
        chunk_args = block.get("args")
        chunk_id = block.get("id")
        chunk_index = block.get("index")

        buffer_key: str | int
        if chunk_index is not None:
            buffer_key = chunk_index
        elif chunk_id is not None:
            buffer_key = chunk_id
        else:
            buffer_key = f"unknown-{len(tool_call_buffers)}"

        buffer = tool_call_buffers.setdefault(
            buffer_key,
            {"name": None, "id": None, "args": None, "args_parts": []},
        )

        if chunk_name:
            buffer["name"] = chunk_name
        if chunk_id:
            buffer["id"] = chunk_id

        if isinstance(chunk_args, dict):
            buffer["args"] = chunk_args
            buffer["args_parts"] = []
        elif isinstance(chunk_args, str):
            if chunk_args:
                parts: list[str] = buffer.setdefault("args_parts", [])
                if not parts or chunk_args != parts[-1]:
                    parts.append(chunk_args)
                buffer["args"] = "".join(parts)
        elif chunk_args is not None:
            buffer["args"] = chunk_args


def create_content_block_handler_chain() -> ContentBlockHandler:
    """Create a chain of content block handlers."""
    text_handler = TextBlockHandler()
    tool_call_handler = ToolCallBlockHandler()

    text_handler.set_next(tool_call_handler)

    return text_handler


class ArgParsingHandler(ABC):
    """Abstract base class for argument parsing strategies."""

    def __init__(self, next_handler: "ArgParsingHandler" = None):
        self.next_handler = next_handler

    def set_next(self, handler: "ArgParsingHandler") -> "ArgParsingHandler":
        """Set the next handler in the chain."""
        self.next_handler = handler
        return handler

    def parse(self, parsed_args: Any) -> Any:
        """Parse arguments, returning processed args or None."""
        if self.can_parse(parsed_args):
            return self._parse_specific(parsed_args)
        elif self.next_handler:
            return self.next_handler.parse(parsed_args)
        else:
            return parsed_args

    @abstractmethod
    def can_parse(self, parsed_args: Any) -> bool:
        """Check if this handler can parse the given args."""

    @abstractmethod
    def _parse_specific(self, parsed_args: Any) -> Any:
        """Parse the args specifically for this handler type."""


class StringArgParsingHandler(ArgParsingHandler):
    """Handler for string argument parsing."""

    def can_parse(self, parsed_args: Any) -> bool:
        return isinstance(parsed_args, str)

    def _parse_specific(self, parsed_args: Any) -> Any:
        if not parsed_args:
            return None
        try:
            return json.loads(parsed_args)
        except Exception:
            return None  # Return None to indicate parsing failure


class NoneArgParsingHandler(ArgParsingHandler):
    """Handler for None argument parsing."""

    def can_parse(self, parsed_args: Any) -> bool:
        return parsed_args is None

    def _parse_specific(self, parsed_args: Any) -> Any:
        return None  # Keep as None


def create_arg_parsing_chain() -> ArgParsingHandler:
    """Create a chain of argument parsing handlers."""
    string_handler = StringArgParsingHandler()
    none_handler = NoneArgParsingHandler()

    string_handler.set_next(none_handler)

    return string_handler
