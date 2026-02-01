"""Main entry point and CLI loop for swe-workflow."""
# ruff: noqa: T201, E402, BLE001, PLR0912, PLR0915

# Suppress deprecation warnings from langchain_core (e.g., Pydantic V1 on Python 3.14+)
# ruff: noqa: E402
import warnings

warnings.filterwarnings("ignore", module="langchain_core._api.deprecation")

import argparse
import asyncio
import contextlib
import os
import sys
import warnings
from pathlib import Path

# Suppress Pydantic v1 compatibility warnings from langchain on Python 3.14+
warnings.filterwarnings("ignore", message=".*Pydantic V1.*", category=UserWarning)

from rich.text import Text

from ._version import __version__

# Now safe to import agent (which imports LangChain modules)
from .agent import create_cli_agent, list_agents, reset_agent
from .non_interactive import run_non_interactive_with_resume

# CRITICAL: Import config FIRST to set LANGSMITH_PROJECT before LangChain loads
from .config import (
    console,
    create_model,
    settings,
)
from .sessions import (
    delete_thread_command,
    generate_thread_id,
    get_checkpointer,
    get_most_recent,
    get_thread_agent,
    list_threads_command,
    thread_exists,
)
from .skills import execute_skills_command, setup_skills_parser
from .tools import fetch_url, http_request
from .ui import show_help


def check_cli_dependencies() -> None:
    """Check if CLI optional dependencies are installed."""
    missing = []

    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")

    try:
        import dotenv  # noqa: F401
    except ImportError:
        missing.append("python-dotenv")


    try:
        import textual  # noqa: F401
    except ImportError:
        missing.append("textual")

    if missing:
        print("\n❌ Missing required CLI dependencies!")
        print("\nThe following packages are required to use the swe-workflow CLI:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease install them with:")
        print("  pip install swe-workflow")
        print("\nOr install all dependencies:")
        print("  pip install 'swe-workflow'")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SWE-Workflow - AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"swe-workflow {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all available agents")

    # Help command
    subparsers.add_parser("help", help="Show help information")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset an agent")
    reset_parser.add_argument("--agent", required=True, help="Name of agent to reset")
    reset_parser.add_argument(
        "--target", dest="source_agent", help="Copy prompt from another agent"
    )

    # Skills command - setup delegated to skills module
    setup_skills_parser(subparsers)

    # Threads command
    threads_parser = subparsers.add_parser("threads", help="Manage conversation threads")
    threads_sub = threads_parser.add_subparsers(dest="threads_command")

    # threads list
    threads_list = threads_sub.add_parser("list", help="List threads")
    threads_list.add_argument(
        "--agent", default=None, help="Filter by agent name (default: show all)"
    )
    threads_list.add_argument("--limit", type=int, default=20, help="Max threads (default: 20)")

    # threads delete
    threads_delete = threads_sub.add_parser("delete", help="Delete a thread")
    threads_delete.add_argument("thread_id", help="Thread ID to delete")

    # Default interactive mode
    parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for separate memory stores (default: agent).",
    )

    # Thread resume argument - matches PR #638: -r for most recent, -r <ID> for specific
    parser.add_argument(
        "-r",
        "--resume",
        dest="resume_thread",
        nargs="?",
        const="__MOST_RECENT__",
        default=None,
        help="Resume thread: -r for most recent, -r <ID> for specific thread",
    )

    # Initial prompt - auto-submit when session starts
    parser.add_argument(
        "-m",
        "--message",
        dest="initial_prompt",
        help="Initial prompt to auto-submit when session starts",
    )

    parser.add_argument(
        "--model",
        help="Model to use (e.g., claude-sonnet-4-5-20250929, gpt-5-mini, devstral-small-2). "
        "Provider is auto-detected from model name.",
    )
    parser.add_argument(
        "--openai-compatible-url",
        help="URL for OpenAI-compatible API endpoint (e.g., http://localhost:11434/v1 for Ollama)",
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve tool usage without prompting (disables human-in-the-loop)",
    )
    parser.add_argument(
        "--non-interactive",
        "--batch",
        action="store_true",
        help="Run in non-interactive mode without UI, auto-approving all actions",
    )
    parser.add_argument(
        "--task",
        help="Task to execute in non-interactive mode",
    )
    return parser.parse_args()


async def run_textual_cli_async(
    assistant_id: str,
    *,
    auto_approve: bool = False,
    model_name: str | None = None,
    thread_id: str | None = None,
    is_resumed: bool = False,
    initial_prompt: str | None = None,
) -> None:
    """Run the Textual CLI interface (async version).

    Args:
        assistant_id: Agent identifier for memory storage
        auto_approve: Whether to auto-approve tool usage
        model_name: Optional model name to use
        thread_id: Thread ID to use (new or resumed)
        is_resumed: Whether this is a resumed session
        initial_prompt: Optional prompt to auto-submit when session starts
    """
    from .app import run_textual_app

    model = create_model(model_name)

    # Show thread info
    if is_resumed:
        console.print(f"[green]Resuming thread:[/green] {thread_id}")
    else:
        console.print(f"[dim]Thread: {thread_id}[/dim]")

    # Use async context manager for checkpointer
    async with get_checkpointer() as checkpointer:
        # Create agent with conditional tools
        tools = [http_request, fetch_url]

        try:
            agent, composite_backend = create_cli_agent(
                model=model,
                assistant_id=assistant_id,
                tools=tools,
                auto_approve=auto_approve,
                checkpointer=checkpointer,
            )

            # Run Textual app
            await run_textual_app(
                agent=agent,
                assistant_id=assistant_id,
                backend=composite_backend,
                auto_approve=auto_approve,
                cwd=Path.cwd(),
                thread_id=thread_id,
                initial_prompt=initial_prompt,
            )
        except Exception as e:
            error_text = Text("❌ Failed to create agent: ", style="red")
            error_text.append(str(e))
            console.print(error_text)
            sys.exit(1)
        finally:
            pass


def cli_main() -> None:
    """Entry point for console script."""
    # Fix for gRPC fork issue on macOS
    # https://github.com/grpc/grpc/issues/37642
    if sys.platform == "darwin":
        os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "0"

    # Note: LANGSMITH_PROJECT is already overridden in config.py (before LangChain imports)
    # This ensures agent traces → LANGSMITH_PROJECT
    # Shell commands → user's original LANGSMITH_PROJECT (via ShellMiddleware env)

    # Check dependencies first
    check_cli_dependencies()

    try:
        args = parse_args()

        if args.command == "help":
            show_help()
        elif args.command == "list":
            list_agents()
        elif args.command == "reset":
            reset_agent(args.agent, args.source_agent)
        elif args.command == "skills":
            execute_skills_command(args)
        elif args.command == "threads":
            if args.threads_command == "list":
                asyncio.run(
                    list_threads_command(
                        agent_name=getattr(args, "agent", None),
                        limit=getattr(args, "limit", 20),
                    )
                )
            elif args.threads_command == "delete":
                asyncio.run(delete_thread_command(args.thread_id))
            else:
                console.print("[yellow]Usage: swe-workflow threads <list|delete>[/yellow]")
        else:
            # Check if running in non-interactive mode
            if args.non_interactive:
                # Non-interactive mode - run without UI
                thread_id = None
                is_resumed = False

                if args.resume_thread == "__MOST_RECENT__":
                    # -r (no ID): Get most recent thread
                    agent_filter = args.agent if args.agent != "agent" else None
                    thread_id = asyncio.run(get_most_recent(agent_filter))
                    if thread_id:
                        is_resumed = True
                        agent_name = asyncio.run(get_thread_agent(thread_id))
                        if agent_name:
                            args.agent = agent_name
                    else:
                        if agent_filter:
                            print(f"No previous thread for '{args.agent}', starting new.")
                        else:
                            print("No previous threads, starting new.")

                elif args.resume_thread:
                    # -r <ID>: Resume specific thread
                    if asyncio.run(thread_exists(args.resume_thread)):
                        thread_id = args.resume_thread
                        is_resumed = True
                        if args.agent == "agent":
                            agent_name = asyncio.run(get_thread_agent(thread_id))
                            if agent_name:
                                args.agent = agent_name
                    else:
                        print(f"Thread '{args.resume_thread}' not found.")
                        print("Use 'swe-workflow threads list' to see available threads.")
                        sys.exit(1)

                # Generate new thread ID if not resuming
                if thread_id is None:
                    thread_id = generate_thread_id()

                # Handle OpenAI-compatible API configuration from command line
                # If openai-compatible URL is provided, set up the configuration and mark for use
                if hasattr(args, "openai_compatible_url") and args.openai_compatible_url:
                    os.environ["OPENAI_COMPATIBLE_URL"] = args.openai_compatible_url
                    # Update both environment variable and internal setting
                    settings.openai_compatible_url = args.openai_compatible_url
                    os.environ["USE_OPENAI_COMPATIBLE"] = (
                        "1"  # Flag to indicate OpenAI-compatible API usage
                    )
                    # If no model was specified but we have an openai-compatible URL,
                    # we should use a default model or let the config system handle it
                    if not hasattr(args, "model") or not args.model:
                        # Default will be used if no --model specified
                        pass

                # Use the model from --model argument
                model_name = getattr(args, "model", None)

                # Run non-interactive mode with resume capability
                exit_code = asyncio.run(
                    run_non_interactive_with_resume(
                        task=args.task or "",
                        assistant_id=args.agent,
                        auto_approve=True,  # Always auto-approve in non-interactive mode
                        model_name=model_name,
                        resume_thread_id=thread_id if is_resumed else None,
                        initial_prompt=getattr(args, "initial_prompt", None),
                    )
                )
                sys.exit(exit_code)
            else:
                # Interactive mode - handle thread resume
                thread_id = None
                is_resumed = False

                if args.resume_thread == "__MOST_RECENT__":
                    # -r (no ID): Get most recent thread
                    # If --agent specified, filter by that agent; otherwise get most recent overall
                    agent_filter = args.agent if args.agent != "agent" else None
                    thread_id = asyncio.run(get_most_recent(agent_filter))
                    if thread_id:
                        is_resumed = True
                        agent_name = asyncio.run(get_thread_agent(thread_id))
                        if agent_name:
                            args.agent = agent_name
                    else:
                        if agent_filter:
                            msg = Text("No previous thread for '", style="yellow")
                            msg.append(args.agent)
                            msg.append("', starting new.", style="yellow")
                        else:
                            msg = Text("No previous threads, starting new.", style="yellow")
                        console.print(msg)

                elif args.resume_thread:
                    # -r <ID>: Resume specific thread
                    if asyncio.run(thread_exists(args.resume_thread)):
                        thread_id = args.resume_thread
                        is_resumed = True
                        if args.agent == "agent":
                            agent_name = asyncio.run(get_thread_agent(thread_id))
                            if agent_name:
                                args.agent = agent_name
                    else:
                        error_msg = Text("Thread '", style="red")
                        error_msg.append(args.resume_thread)
                        error_msg.append("' not found.", style="red")
                        console.print(error_msg)
                        console.print(
                            "[dim]Use 'swe-workflow threads list' to see available threads.[/dim]"
                        )
                        sys.exit(1)

                # Generate new thread ID if not resuming
                if thread_id is None:
                    thread_id = generate_thread_id()

                # Handle OpenAI-compatible API configuration from command line
                # If openai-compatible URL is provided, set up the configuration and mark for use
                if hasattr(args, "openai_compatible_url") and args.openai_compatible_url:
                    os.environ["OPENAI_COMPATIBLE_URL"] = args.openai_compatible_url
                    # Update both environment variable and internal setting
                    settings.openai_compatible_url = args.openai_compatible_url
                    os.environ["USE_OPENAI_COMPATIBLE"] = (
                        "1"  # Flag to indicate OpenAI-compatible API usage
                    )
                    # If no model was specified but we have an openai-compatible URL,
                    # we should use a default model or let the config system handle it
                    if not hasattr(args, "model") or not args.model:
                        # Default will be used if no --model specified
                        pass

                # Use the model from --model argument
                model_name = getattr(args, "model", None)

                # Run Textual CLI
                asyncio.run(
                    run_textual_cli_async(
                        assistant_id=args.agent,
                        auto_approve=args.auto_approve,
                        model_name=model_name,
                        thread_id=thread_id,
                        is_resumed=is_resumed,
                        initial_prompt=getattr(args, "initial_prompt", None),
                    )
                )
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C - suppress ugly traceback
        console.print("\n\n[yellow]Interrupted[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
