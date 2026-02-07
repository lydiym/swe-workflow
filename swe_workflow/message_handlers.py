"""Message handling strategies using the Strategy pattern to replace if/elif chains."""

import json
from abc import ABC, abstractmethod
from typing import Any


class MessageHandler(ABC):
    """Abstract base class for message handling strategies."""

    def __init__(self, next_handler: "MessageHandler" = None):
        self.next_handler = next_handler

    def set_next(self, handler: "MessageHandler") -> "MessageHandler":
        """Set the next handler in the chain."""
        self.next_handler = handler
        return handler

    async def handle(self, msg: Any, app_instance: Any) -> bool:
        """Handle a message, returning True if handled, False otherwise."""
        if self.can_handle(msg):
            await self._handle_specific(msg, app_instance)
            return True
        if self.next_handler:
            return await self.next_handler.handle(msg, app_instance)
        return False

    @abstractmethod
    def can_handle(self, msg: Any) -> bool:
        """Check if this handler can handle the given message."""

    @abstractmethod
    async def _handle_specific(self, msg: Any, app_instance: Any) -> None:
        """Handle the message specifically for this handler type."""


class UserMessageHandler(MessageHandler):
    """Handler for user/human messages."""

    async def _handle_specific(self, msg: Any, app_instance: Any) -> None:
        content = app_instance._extract_message_content(msg)
        message_widget = app_instance.UserMessage(content)
        await app_instance._mount_message(message_widget)

    def can_handle(self, msg: Any) -> bool:
        msg_class_name = type(msg).__name__.lower()
        return msg.type == "human" or "human" in msg_class_name or "user" in msg_class_name


class AssistantMessageHandler(MessageHandler):
    """Handler for AI/assistant messages without tool calls."""

    async def _handle_specific(self, msg: Any, app_instance: Any) -> None:
        content = app_instance._extract_message_content(msg)
        message_widget = app_instance.AssistantMessage(content)
        await app_instance._mount_message(message_widget)
        await message_widget.write_initial_content()

    def can_handle(self, msg: Any) -> bool:
        msg_class_name = type(msg).__name__.lower()
        return (msg.type == "ai" or "ai" in msg_class_name or "assistant" in msg_class_name) and not (hasattr(msg, "tool_calls") and msg.tool_calls)


class AssistantWithToolCallsMessageHandler(MessageHandler):
    """Handler for AI/assistant messages with tool calls."""

    async def _handle_specific(self, msg: Any, app_instance: Any) -> None:
        tool_results = getattr(app_instance, "_tool_results", {})

        for tc in msg.tool_calls:
            tool_name = tc.get("name", "unknown")
            tool_args = tc.get("args", {})
            tool_call_id = tc.get("id", None)

            # Check if there's a corresponding result for this tool call
            if tool_call_id and tool_call_id in tool_results:
                # There is a result, so create the tool call widget and immediately set its status
                message_widget = app_instance.ToolCallMessage(tool_name=tool_name, args=tool_args)
                await app_instance._mount_message(message_widget)

                # Get the result message and set the status
                result_msg = tool_results[tool_call_id]
                result_content = app_instance._extract_message_content(result_msg)

                if hasattr(result_msg, "status") and result_msg.status == "error":
                    message_widget.set_error(result_content if result_content else "Tool execution failed")
                else:
                    message_widget.set_success(result_content if result_content else "Tool executed successfully")
            else:
                # No result yet, create pending tool call
                message_widget = app_instance.ToolCallMessage(tool_name=tool_name, args=tool_args)
                await app_instance._mount_message(message_widget)

                # Add to current tool messages if we have a UI adapter and tool_call_id
                if app_instance._ui_adapter and tool_call_id:
                    app_instance._ui_adapter._current_tool_messages[tool_call_id] = message_widget

    def can_handle(self, msg: Any) -> bool:
        msg_class_name = type(msg).__name__.lower()
        return (msg.type == "ai" or "ai" in msg_class_name or "assistant" in msg_class_name) and hasattr(msg, "tool_calls") and msg.tool_calls


class ToolMessageHandler(MessageHandler):
    """Handler for tool messages (results from tool calls)."""

    async def _handle_specific(self, msg: Any, app_instance: Any) -> None:
        # This is a ToolMessage (result from a tool call), but we've already handled it
        # in the AI message processing above, so we skip it here to avoid duplication
        return

    def can_handle(self, msg: Any) -> bool:
        msg_class_name = type(msg).__name__.lower()
        return msg.type == "tool" or "tool" in msg_class_name


class SystemMessageHandler(MessageHandler):
    """Handler for system messages."""

    async def _handle_specific(self, msg: Any, app_instance: Any) -> None:
        content = app_instance._extract_message_content(msg)
        message_widget = app_instance.SystemMessage(content)
        await app_instance._mount_message(message_widget)

    def can_handle(self, msg: Any) -> bool:
        msg_class_name = type(msg).__name__.lower()
        return msg.type == "system" or "system" in msg_class_name


class DefaultMessageHandler(MessageHandler):
    """Default handler for unrecognized message types."""

    async def _handle_specific(self, msg: Any, app_instance: Any) -> None:
        content = app_instance._extract_message_content(msg)
        message_widget = app_instance.SystemMessage(f"[{msg.type}] {content[:200]}")
        await app_instance._mount_message(message_widget)

    def can_handle(self, msg: Any) -> bool:
        # This handler can handle any message type as a fallback
        return True


def create_message_handler_chain() -> MessageHandler:
    """Create a chain of message handlers."""
    user_handler = UserMessageHandler()
    assistant_handler = AssistantMessageHandler()
    assistant_tool_handler = AssistantWithToolCallsMessageHandler()
    tool_handler = ToolMessageHandler()
    system_handler = SystemMessageHandler()
    default_handler = DefaultMessageHandler()

    user_handler.set_next(assistant_handler)
    assistant_handler.set_next(assistant_tool_handler)
    assistant_tool_handler.set_next(tool_handler)
    tool_handler.set_next(system_handler)
    system_handler.set_next(default_handler)

    return user_handler


class ContentExtractor:
    """Strategy for extracting content from different message types."""

    @staticmethod
    def extract_content(msg: Any) -> str:
        """Extract content from a message using appropriate strategy."""
        content = ""
        msg_class_name = type(msg).__name__.lower()

        if hasattr(msg, "content"):
            msg_content = msg.content

            if isinstance(msg_content, list):
                # Handle content as a list of message parts
                for part in msg_content:
                    if isinstance(part, str):
                        content += part
                    elif isinstance(part, dict):
                        # Handle dictionary content
                        if "text" in part:
                            content += str(part["text"])
                        elif "content" in part:
                            content += str(part["content"])
                        else:
                            content += str(part)
                    elif hasattr(part, "text"):
                        content += str(part.text)
                    elif hasattr(part, "data"):
                        content += str(part.data)
                    else:
                        content += str(part)
            elif hasattr(msg_content, "__iter__") and not isinstance(msg_content, str):
                # Handle other iterable content
                try:
                    content = "".join(str(item) for item in msg_content)
                except TypeError:
                    # If iteration fails, convert to string directly
                    content = str(msg_content)
            else:
                # Handle simple string content
                content = str(msg_content)
        elif hasattr(msg, "text"):  # For some message types that use 'text' instead of 'content'
            content = str(getattr(msg, "text", ""))
        else:
            # If no known content attribute, convert the whole message to string
            content = str(msg)

        return content
