"""Non-interactive mode execution for swe-workflow."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langgraph.types import Command, Interrupt
from pydantic import TypeAdapter

from .agent import create_cli_agent
from .config import create_model, settings
from .file_ops import FileOpTracker
from .image_utils import create_multimodal_content
from .input import ImageTracker, parse_file_mentions
from .sessions import get_checkpointer, generate_thread_id
from .tools import fetch_url, http_request, web_search


_HITL_REQUEST_ADAPTER = TypeAdapter(dict)  # Simplified for non-interactive mode


async def execute_task_non_interactive(
    user_input: str,
    agent: Any,
    assistant_id: str | None,
    thread_id: str,
    backend: Any = None,
    image_tracker: ImageTracker | None = None,
    auto_approve: bool = True,
) -> bool:
    """Execute a task in non-interactive mode without UI.

    Args:
        user_input: The user's input message
        agent: The LangGraph agent to execute
        assistant_id: The agent identifier
        thread_id: The thread ID for session persistence
        backend: Optional backend for file operations
        image_tracker: Optional tracker for images
        auto_approve: Whether to auto-approve all tool calls

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Parse file mentions and inject content if any
        prompt_text, mentioned_files = parse_file_mentions(user_input)

        # Max file size to embed inline (256KB, matching mistral-vibe)
        # Larger files get a reference instead - use read_file tool to view them
        max_embed_bytes = 256 * 1024

        if mentioned_files:
            context_parts = [prompt_text, "\n\n## Referenced Files\n"]
            for file_path in mentioned_files:
                try:
                    file_size = file_path.stat().st_size
                    if file_size > max_embed_bytes:
                        # File too large - include reference instead of content
                        size_kb = file_size // 1024
                        context_parts.append(f"\n### {file_path.name}\nPath: `{file_path}`\nSize: {size_kb}KB (too large to embed, use read_file tool to view)")
                    else:
                        content = file_path.read_text()
                        context_parts.append(f"\n### {file_path.name}\nPath: `{file_path}`\n```\n{content}\n```")
                except Exception as e:
                    context_parts.append(f"\n### {file_path.name}\n[Error reading file: {e}]")
            final_input = "\n".join(context_parts)
        else:
            final_input = prompt_text

        # Include images in the message content
        images_to_send = []
        if image_tracker:
            images_to_send = image_tracker.get_images()
        if images_to_send:
            message_content = create_multimodal_content(final_input, images_to_send)
        else:
            message_content = final_input

        config = {
            "configurable": {"thread_id": thread_id},
            "metadata": {
                "assistant_id": assistant_id,
                "agent_name": assistant_id,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            if assistant_id
            else {},
        }

        file_op_tracker = FileOpTracker(assistant_id=assistant_id, backend=backend)
        tool_call_buffers = {}

        stream_input: dict | Command = {"messages": [{"role": "user", "content": message_content}]}

        while True:
            interrupt_occurred = False
            hitl_response: dict[str, Any] = {}

            async for chunk in agent.astream(
                stream_input,
                stream_mode=["messages", "updates"],
                subgraphs=True,
                config=config,
                durability="exit",
            ):
                if not isinstance(chunk, tuple) or len(chunk) != 3:
                    continue

                namespace, current_stream_mode, data = chunk

                # Filter out subagent outputs - only show main agent (empty namespace)
                # Subagents run via Task tool and should only report back to the main agent
                is_main_agent = namespace == () or namespace == []

                # Handle UPDATES stream - for interrupts and todos
                if current_stream_mode == "updates":
                    if not isinstance(data, dict):
                        continue

                    # Check for interrupts
                    if "__interrupt__" in data:
                        interrupts: list[Interrupt] = data["__interrupt__"]
                        if interrupts:
                            for interrupt_obj in interrupts:
                                interrupt_occurred = True

                    # Check for todo updates (not yet implemented in non-interactive mode)
                    chunk_data = next(iter(data.values())) if data else None
                    if chunk_data and isinstance(chunk_data, dict) and "todos" in chunk_data:
                        pass  # Future: handle todo updates

                # Handle MESSAGES stream - for content and tool calls
                elif current_stream_mode == "messages":
                    # Skip subagent outputs - only process main agent content
                    if not is_main_agent:
                        continue

                    if not isinstance(data, tuple) or len(data) != 2:
                        continue

                    message, _metadata = data

                    # Process tool messages
                    if isinstance(message, ToolMessage):
                        tool_name = getattr(message, "name", "")
                        tool_status = getattr(message, "status", "success")
                        tool_content = getattr(message, "content", "")

                        # Print tool execution results
                        print(f"[TOOL] {tool_name}: {tool_content[:200]}..." if len(str(tool_content)) > 200 else f"[TOOL] {tool_name}: {tool_content}")

                        # Complete file operation tracking
                        record = file_op_tracker.complete_with_message(message)

                        # Update tool call status
                        tool_id = getattr(message, "tool_call_id", None)
                        if tool_id:
                            # Print tool result
                            if tool_status == "success":
                                print(f"[SUCCESS] Tool {tool_name} completed successfully")
                            else:
                                print(f"[ERROR] Tool {tool_name} failed: {tool_content}")
                        # Add a newline after tool output to separate from agent response
                        print()

                    # Process text content from AI messages
                    if isinstance(message, (AIMessageChunk, AIMessage)):
                        for block in message.content_blocks:
                            block_type = block.get("type")

                            if block_type == "text":
                                text = block.get("text", "")
                                if text:
                                    print(text, end="", flush=True)

                            elif block_type in ("tool_call_chunk", "tool_call"):
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

                                buffer_name = buffer.get("name")
                                buffer_id = buffer.get("id")
                                if buffer_name is None:
                                    continue

                                parsed_args = buffer.get("args")
                                if isinstance(parsed_args, str):
                                    if not parsed_args:
                                        continue
                                    try:
                                        parsed_args = json.loads(parsed_args)
                                    except Exception:
                                        continue
                                elif parsed_args is None:
                                    continue

                                if not isinstance(parsed_args, dict):
                                    parsed_args = {"value": parsed_args}

                                if buffer_id is not None:
                                    file_op_tracker.start_operation(buffer_name, parsed_args, buffer_id)

                                    # Print tool call
                                    print(f"\n[CALLING] {buffer_name} with args: {parsed_args}")

                                tool_call_buffers.pop(buffer_key, None)

            # Handle HITL after stream completes
            if interrupt_occurred:
                # In non-interactive mode with auto-approve, we auto-approve everything
                if auto_approve:
                    # Since we're in auto-approve mode, we continue without user interaction
                    stream_input = Command(resume={})  # Empty resume for auto-approve
                else:
                    # This shouldn't happen in non-interactive mode without auto-approve
                    print("Error: Non-interactive mode requires auto-approve for HITL requests")
                    return False
            else:
                break

        print("\n[COMPLETE] Task execution finished")
        return True

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Task was interrupted by user")
        return False
    except Exception as e:
        print(f"\n[ERROR] Task execution failed: {e}")
        return False


async def run_non_interactive_mode(
    task: str,
    assistant_id: str,
    auto_approve: bool = True,
    model_name: str | None = None,
    thread_id: str | None = None,
    initial_prompt: str | None = None,
) -> None:
    """Run the agent in non-interactive mode.

    Args:
        task: The task to execute
        assistant_id: Agent identifier for memory storage
        auto_approve: Whether to auto-approve tool usage
        model_name: Optional model name to use
        thread_id: Thread ID to use (new or resumed)
        initial_prompt: Optional initial prompt to execute
    """
    model = create_model(model_name)

    # Generate or use provided thread ID
    if thread_id is None:
        thread_id = generate_thread_id()

    print(f"Starting non-interactive task with thread: {thread_id}")

    # Use async context manager for checkpointer
    async with get_checkpointer() as checkpointer:
        # Create agent with conditional tools
        tools = [http_request, fetch_url]
        if settings.has_tavily:
            tools.append(web_search)

        try:
            agent, composite_backend = create_cli_agent(
                model=model,
                assistant_id=assistant_id,
                tools=tools,
                auto_approve=auto_approve,  # Critical for non-interactive mode
                checkpointer=checkpointer,
            )

            # Execute the task
            task_to_run = initial_prompt or task
            if task_to_run:
                await execute_task_non_interactive(
                    user_input=task_to_run,
                    agent=agent,
                    assistant_id=assistant_id,
                    thread_id=thread_id,
                    backend=composite_backend,
                    auto_approve=auto_approve,
                )
            else:
                print("No task provided to execute")

        except Exception as e:
            print(f"❌ Failed to execute task: {e}")
            raise
        finally:
            pass


async def run_non_interactive_with_resume(
    task: str,
    assistant_id: str,
    auto_approve: bool = True,
    model_name: str | None = None,
    resume_thread_id: str | None = None,
    initial_prompt: str | None = None,
) -> int:
    """Run the agent in non-interactive mode with thread resume capability.

    Args:
        task: The task to execute
        assistant_id: Agent identifier for memory storage
        auto_approve: Whether to auto-approve tool usage
        model_name: Optional model name to use
        resume_thread_id: Thread ID to resume (None for new thread)
        initial_prompt: Optional initial prompt to execute

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    model = create_model(model_name)

    # Use provided thread ID or generate a new one
    thread_id = resume_thread_id if resume_thread_id is not None else generate_thread_id()
    is_resumed = resume_thread_id is not None

    if is_resumed:
        print(f"Resuming non-interactive task with thread: {thread_id}")
    else:
        print(f"Starting new non-interactive task with thread: {thread_id}")

    # Use async context manager for checkpointer
    async with get_checkpointer() as checkpointer:
        # Create agent with conditional tools
        tools = [http_request, fetch_url]
        if settings.has_tavily:
            tools.append(web_search)

        try:
            agent, composite_backend = create_cli_agent(
                model=model,
                assistant_id=assistant_id,
                tools=tools,
                auto_approve=auto_approve,  # Critical for non-interactive mode
                checkpointer=checkpointer,
            )

            # Execute the task
            task_to_run = initial_prompt or task
            if task_to_run:
                success = await execute_task_non_interactive(
                    user_input=task_to_run,
                    agent=agent,
                    assistant_id=assistant_id,
                    thread_id=thread_id,
                    backend=composite_backend,
                    auto_approve=auto_approve,
                )

                if not success:
                    return 1  # Exit with error code
            else:
                print("No task provided to execute")
                return 1  # Exit with error code

        except Exception as e:
            print(f"❌ Failed to execute task: {e}")
            return 1  # Exit with error code
        finally:
            pass

    return 0  # Exit with success code
