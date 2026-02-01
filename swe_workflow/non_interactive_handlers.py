"""Non-interactive message handling strategies using the Strategy pattern to replace if/elif chains."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import json


class StreamModeHandler(ABC):
    """Abstract base class for stream mode handling strategies."""
    
    def __init__(self, next_handler: 'StreamModeHandler' = None):
        self.next_handler = next_handler
    
    def set_next(self, handler: 'StreamModeHandler') -> 'StreamModeHandler':
        """Set the next handler in the chain."""
        self.next_handler = handler
        return handler
    
    def handle(self, current_stream_mode: str, data: Any, is_main_agent: bool, 
               file_op_tracker: Any, tool_call_buffers: Dict, print_func: Any = print) -> bool:
        """Handle stream mode data, returning True if handled, False otherwise."""
        if self.can_handle(current_stream_mode):
            self._handle_specific(data, is_main_agent, file_op_tracker, tool_call_buffers, print_func)
            return True
        elif self.next_handler:
            return self.next_handler.handle(current_stream_mode, data, is_main_agent, file_op_tracker, tool_call_buffers, print_func)
        else:
            return False
    
    @abstractmethod
    def can_handle(self, current_stream_mode: str) -> bool:
        """Check if this handler can handle the given stream mode."""
        pass
    
    @abstractmethod
    def _handle_specific(self, data: Any, is_main_agent: bool, file_op_tracker: Any, 
                        tool_call_buffers: Dict, print_func: Any) -> None:
        """Handle the data specifically for this stream mode."""
        pass


class MessagesStreamHandler(StreamModeHandler):
    """Handler for MESSAGES stream mode."""
    
    def can_handle(self, current_stream_mode: str) -> bool:
        return current_stream_mode == "messages"
    
    def _handle_specific(self, data: Any, is_main_agent: bool, file_op_tracker: Any, 
                        tool_call_buffers: Dict, print_func: Any) -> None:
        # Skip subagent outputs - only process main agent content
        if not is_main_agent:
            return

        if not isinstance(data, tuple) or len(data) != 2:
            return

        message, _metadata = data

        # Process messages using message handlers
        from .message_type_handlers import create_message_type_handler_chain
        handler_chain = create_message_type_handler_chain()
        handler_chain.handle(message, file_op_tracker, tool_call_buffers, print_func)


def create_stream_mode_handler_chain() -> StreamModeHandler:
    """Create a chain of stream mode handlers."""
    messages_handler = MessagesStreamHandler()
    
    return messages_handler


class MessageTypeHandler(ABC):
    """Abstract base class for message type handling strategies."""
    
    def __init__(self, next_handler: 'MessageTypeHandler' = None):
        self.next_handler = next_handler
    
    def set_next(self, handler: 'MessageTypeHandler') -> 'MessageTypeHandler':
        """Set the next handler in the chain."""
        self.next_handler = handler
        return handler
    
    def handle(self, message: Any, file_op_tracker: Any, tool_call_buffers: Dict, print_func: Any = print) -> bool:
        """Handle a message, returning True if handled, False otherwise."""
        if self.can_handle(message):
            self._handle_specific(message, file_op_tracker, tool_call_buffers, print_func)
            return True
        elif self.next_handler:
            return self.next_handler.handle(message, file_op_tracker, tool_call_buffers, print_func)
        else:
            return False
    
    @abstractmethod
    def can_handle(self, message: Any) -> bool:
        """Check if this handler can handle the given message type."""
        pass
    
    @abstractmethod
    def _handle_specific(self, message: Any, file_op_tracker: Any, tool_call_buffers: Dict, print_func: Any) -> None:
        """Handle the message specifically for this message type."""
        pass


class ToolMessageHandler(MessageTypeHandler):
    """Handler for ToolMessage instances."""
    
    def can_handle(self, message: Any) -> bool:
        from langchain_core.messages import ToolMessage
        return isinstance(message, ToolMessage)
    
    def _handle_specific(self, message: Any, file_op_tracker: Any, tool_call_buffers: Dict, print_func: Any) -> None:
        tool_name = getattr(message, "name", "")
        tool_status = getattr(message, "status", "success")
        tool_content = getattr(message, "content", "")

        # Print tool execution results
        content_str = str(tool_content)
        content_preview = content_str[:200] + "..." if len(content_str) > 200 else content_str
        print_func(f"[TOOL] {tool_name}: {content_preview}")

        # Complete file operation tracking
        record = file_op_tracker.complete_with_message(message)

        # Update tool call status
        tool_id = getattr(message, "tool_call_id", None)
        if tool_id:
            # Print tool result
            if tool_status == "success":
                print_func(f"[SUCCESS] Tool {tool_name} completed successfully")
            else:
                print_func(f"[ERROR] Tool {tool_name} failed: {tool_content}")
        # Add a newline after tool output to separate from agent response
        print_func()


class AIAndAIMessageChunkHandler(MessageTypeHandler):
    """Handler for AIMessageChunk and AIMessage instances."""
    
    def can_handle(self, message: Any) -> bool:
        from langchain_core.messages import AIMessage, AIMessageChunk
        return isinstance(message, (AIMessageChunk, AIMessage))
    
    def _handle_specific(self, message: Any, file_op_tracker: Any, tool_call_buffers: Dict, print_func: Any) -> None:
        # Process content blocks using content block handlers
        from .content_block_handlers import create_content_block_handler_chain, create_arg_parsing_chain
        block_handler_chain = create_content_block_handler_chain()
        arg_handler_chain = create_arg_parsing_chain()
        
        for block in getattr(message, 'content_blocks', []):
            block_type = block.get("type")
            
            # Handle the content block
            block_handler_chain.handle(block, tool_call_buffers, print_func)

        # Process buffered tool calls (similar to the original logic)
        # Make a copy of the keys to iterate over since we might modify the dict during iteration
        for buffer_key in list(tool_call_buffers.keys()):
            buffer = tool_call_buffers[buffer_key]
            buffer_name = buffer.get("name")
            buffer_id = buffer.get("id")
            if buffer_name is None:
                continue

            parsed_args = buffer.get("args")
            parsed_args = arg_handler_chain.parse(parsed_args)

            if parsed_args is None:
                continue

            if not isinstance(parsed_args, dict):
                parsed_args = {"value": parsed_args}

            if buffer_id is not None:
                file_op_tracker.start_operation(buffer_name, parsed_args, buffer_id)

                # Print tool call
                print_func(f"\n[CALLING] {buffer_name} with args: {parsed_args}")

            # Remove the processed buffer
            tool_call_buffers.pop(buffer_key, None)


def create_message_type_handler_chain() -> MessageTypeHandler:
    """Create a chain of message type handlers."""
    tool_handler = ToolMessageHandler()
    ai_handler = AIAndAIMessageChunkHandler()
    
    tool_handler.set_next(ai_handler)
    
    return tool_handler