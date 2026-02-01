"""Configuration, constants, and model creation for the CLI."""

import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import dotenv
from rich.console import Console

from ._version import __version__

dotenv.load_dotenv()

# CRITICAL: Override LANGSMITH_PROJECT to route agent traces to separate project
# LangSmith reads LANGSMITH_PROJECT at invocation time, so we override it here
# and preserve the user's original value for shell commands
_langsmith_project = os.environ.get("LANGSMITH_PROJECT")
_original_langsmith_project = os.environ.get("LANGSMITH_PROJECT")
if _langsmith_project:
    # Override LANGSMITH_PROJECT for agent traces
    os.environ["LANGSMITH_PROJECT"] = _langsmith_project

# Now safe to import LangChain modules
from langchain_core.language_models import BaseChatModel

COLORS = {
    "primary": "#ca8a04",  # Mustard gold (WCAG compliant on dark)
    "dim": "#78716c",  # Warm gray (meets contrast requirements)
    "user": "#ffffff",  # White (max contrast)
    "agent": "#ca8a04",  # Same contrast as primary
    "thinking": "#1d4ed8",  # Darker blue for better contrast
    "tool": "#b91c1c",  # Darker red for better contrast
}

# ASCII art banner

DEEP_AGENTS_ASCII = f"""
███████╗ ██╗    ██╗ ███████╗
██╔════╝ ██║    ██║ ██╔════╝
███████╗ ██║ █╗ ██║ █████╗
╚════██║ ██║███╗██║ ██╔══╝
███████║ ╚███╔███╔╝ ███████╗
╚══════╝  ╚══╝╚══╝  ╚══════╝
 
██╗    ██╗  ██████╗  ██████╗  ██╗  ██╗ ███████╗ ██╗       ██████╗  ██╗    ██╗
██║    ██║ ██╔═══██╗ ██╔══██╗ ██║ ██╔╝ ██╔════╝ ██║      ██╔═══██╗ ██║    ██║
██║ █╗ ██║ ██║   ██║ ██████╔╝ █████╔╝  █████╗   ██║      ██║   ██║ ██║ █╗ ██║
██║███╗██║ ██║   ██║ ██╔══██╗ ██╔═██╗  ██╔══╝   ██║      ██║   ██║ ██║███╗██║
╚███╔███╔╝ ╚██████╔╝ ██║  ██║ ██║  ██╗ ██║      ███████╗ ╚██████╔╝ ╚███╔███╔╝
 ╚══╝╚══╝   ╚═════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝      ╚══════╝  ╚═════╝   ╚══╝╚══╝
                                                                v{__version__}
"""

# Interactive commands
COMMANDS = {
    "clear": "Clear screen and reset conversation",
    "help": "Show help information",
    "tokens": "Show token usage for current session",
    "quit": "Exit the CLI",
    "exit": "Exit the CLI",
}


# Maximum argument length for display
MAX_ARG_LENGTH = 150

# Agent configuration
config = {"recursion_limit": 1000}

# Rich console instance
console = Console(highlight=False)


def _find_project_root(start_path: Path | None = None) -> Path | None:
    """Find the project root by looking for .git directory.

    Walks up the directory tree from start_path (or cwd) looking for a .git
    directory, which indicates the project root.

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        Path to the project root if found, None otherwise.
    """
    current = Path(start_path or Path.cwd()).resolve()

    # Walk up the directory tree
    for parent in [current, *list(current.parents)]:
        git_dir = parent / ".git"
        if git_dir.exists():
            return parent

    return None


def _find_project_agent_md(project_root: Path) -> list[Path]:
    """Find project-specific AGENTS.md file(s).

    Checks two locations and returns ALL that exist:
    1. project_root/.swe-workflow/AGENTS.md
    2. project_root/AGENTS.md

    Both files will be loaded and combined if both exist.

    Args:
        project_root: Path to the project root directory.

    Returns:
        List of paths to project AGENTS.md files (may contain 0, 1, or 2 paths).
    """
    paths = []

    # Check .swe-workflow/AGENTS.md (preferred)
    agents_md = project_root / ".swe-workflow" / "AGENTS.md"
    if agents_md.exists():
        paths.append(agents_md)

    # Check root AGENTS.md (fallback, but also include if both exist)
    root_md = project_root / "AGENTS.md"
    if root_md.exists():
        paths.append(root_md)

    return paths


@dataclass
class Settings:
    """Global settings and environment detection.

    This class is initialized once at startup and provides access to:
    - Available models and API keys
    - Current project information
    - Tool availability
    - File system paths

    Attributes:
        project_root: Current project root directory (if in a git project)

        openai_api_key: OpenAI API key if available
        anthropic_api_key: Anthropic API key if available
        langchain_project: LangSmith project name for swe-workflow agent tracing
        user_langchain_project: Original LANGSMITH_PROJECT from environment (for user code)
    """

    # API keys
    openai_api_key: str | None
    anthropic_api_key: str | None
    google_api_key: str | None
    openai_compatible_api_key: str | None

    # LangSmith configuration
    langchain_project: str | None  # For swe-workflow agent tracing
    user_langchain_project: str | None  # Original LANGSMITH_PROJECT for user code

    # Model configuration
    model_name: str | None = None  # Currently active model name
    model_provider: str | None = None  # Provider (openai, anthropic, google, openai-compatible)

    # Local LLM configuration
    openai_compatible_url: str | None = None  # URL for OpenAI-compatible API

    # Project information
    project_root: Path | None = None

    @classmethod
    def from_environment(cls, *, start_path: Path | None = None) -> "Settings":
        """Create settings by detecting the current environment.

        Args:
            start_path: Directory to start project detection from (defaults to cwd)

        Returns:
            Settings instance with detected configuration
        """
        # Detect API keys
        openai_key = os.environ.get("OPENAI_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        google_key = os.environ.get("GOOGLE_API_KEY")
        openai_compatible_key = os.environ.get(
            "OPENAI_COMPATIBLE_API_KEY", "sk-openai-compatible"
        )  # Default key for OpenAI-compatible APIs

        # Detect OpenAI-compatible API configuration
        # Check for new environment variable first, then fall back to old one for backward compatibility
        openai_compatible_url = os.environ.get("OPENAI_COMPATIBLE_URL")

        # Detect LangSmith configuration
        # LANGSMITH_PROJECT: Project for swe-workflow agent tracing
        # user_langchain_project: User's ORIGINAL LANGSMITH_PROJECT (before override)
        # Note: LANGSMITH_PROJECT was already overridden at module import time (above)
        # so we use the saved original value, not the current os.environ value
        langchain_project = os.environ.get("LANGSMITH_PROJECT")
        user_langchain_project = _original_langsmith_project  # Use saved original!

        # Detect project
        project_root = _find_project_root(start_path)

        return cls(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            google_api_key=google_key,
            openai_compatible_api_key=openai_compatible_key,
            openai_compatible_url=openai_compatible_url,
            langchain_project=langchain_project,
            user_langchain_project=user_langchain_project,
            project_root=project_root,
        )

    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is configured."""
        return self.openai_api_key is not None

    @property
    def has_anthropic(self) -> bool:
        """Check if Anthropic API key is configured."""
        return self.anthropic_api_key is not None

    @property
    def has_google(self) -> bool:
        """Check if Google API key is configured."""
        return self.google_api_key is not None


    @property
    def has_openai_compatible(self) -> bool:
        """Check if OpenAI-compatible configuration is available."""
        return self.openai_compatible_url is not None

    @property
    def has_langchain_project(self) -> bool:
        """Check if LangChain project name is configured."""
        return self.langchain_project is not None

    @property
    def has_project(self) -> bool:
        """Check if currently in a git project."""
        return self.project_root is not None

    @property
    def user_agent_dir(self) -> Path:
        """Get the base user-level .swe-workflow directory.

        Returns:
            Path to ~/.swe-workflow
        """
        return Path.home() / ".swe-workflow"

    def get_user_agent_md_path(self, agent_name: str) -> Path:
        """Get user-level AGENTS.md path for a specific agent.

        Returns path regardless of whether the file exists.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to ~/.swe-workflow/{agent_name}/AGENTS.md
        """
        return Path.home() / ".swe-workflow" / agent_name / "AGENTS.md"

    def get_project_agent_md_path(self) -> Path | None:
        """Get project-level AGENTS.md path.

        Returns path regardless of whether the file exists.

        Returns:
            Path to {project_root}/.swe-workflow/AGENTS.md, or None if not in a project
        """
        if not self.project_root:
            return None
        return self.project_root / ".swe-workflow" / "AGENTS.md"

    @staticmethod
    def _is_valid_agent_name(agent_name: str) -> bool:
        """Validate prevent invalid filesystem paths and security issues."""
        if not agent_name or not agent_name.strip():
            return False
        # Allow only alphanumeric, hyphens, underscores, and whitespace
        return bool(re.match(r"^[a-zA-Z0-9_\-\s]+$", agent_name))

    def get_agent_dir(self, agent_name: str) -> Path:
        """Get the global agent directory path.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to ~/.swe-workflow/{agent_name}
        """
        if not self._is_valid_agent_name(agent_name):
            msg = (
                f"Invalid agent name: {agent_name!r}. "
                "Agent names can only contain letters, numbers, hyphens, underscores, and spaces."
            )
            raise ValueError(msg)
        return Path.home() / ".swe-workflow" / agent_name

    def ensure_agent_dir(self, agent_name: str) -> Path:
        """Ensure the global agent directory exists and return its path.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to ~/.swe-workflow/{agent_name}
        """
        if not self._is_valid_agent_name(agent_name):
            msg = (
                f"Invalid agent name: {agent_name!r}. "
                "Agent names can only contain letters, numbers, hyphens, underscores, and spaces."
            )
            raise ValueError(msg)
        agent_dir = self.get_agent_dir(agent_name)
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir

    def ensure_project_swe_workflow_dir(self) -> Path | None:
        """Ensure the project .swe-workflow directory exists and return its path.

        Returns:
            Path to project .swe-workflow directory, or None if not in a project
        """
        if not self.project_root:
            return None

        project_swe_workflow_dir = self.project_root / ".swe-workflow"
        project_swe_workflow_dir.mkdir(parents=True, exist_ok=True)
        return project_swe_workflow_dir

    def get_user_skills_dir(self, agent_name: str) -> Path:
        """Get user-level skills directory path for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to ~/.swe-workflow/{agent_name}/skills/
        """
        return self.get_agent_dir(agent_name) / "skills"

    def ensure_user_skills_dir(self, agent_name: str) -> Path:
        """Ensure user-level skills directory exists and return its path.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to ~/.swe-workflow/{agent_name}/skills/
        """
        skills_dir = self.get_user_skills_dir(agent_name)
        skills_dir.mkdir(parents=True, exist_ok=True)
        return skills_dir

    def get_project_skills_dir(self) -> Path | None:
        """Get project-level skills directory path.

        Returns:
            Path to {project_root}/.swe-workflow/skills/, or None if not in a project
        """
        if not self.project_root:
            return None
        return self.project_root / ".swe-workflow" / "skills"

    def ensure_project_skills_dir(self) -> Path | None:
        """Ensure project-level skills directory exists and return its path.

        Returns:
            Path to {project_root}/.swe-workflow/skills/, or None if not in a project
        """
        if not self.project_root:
            return None
        skills_dir = self.get_project_skills_dir()
        skills_dir.mkdir(parents=True, exist_ok=True)
        return skills_dir


# Global settings instance (initialized once)
settings = Settings.from_environment()


class SessionState:
    """Holds mutable session state (auto-approve mode, etc)."""

    def __init__(self, auto_approve: bool = False, no_splash: bool = False) -> None:
        self.auto_approve = auto_approve
        self.no_splash = no_splash
        self.exit_hint_until: float | None = None
        self.exit_hint_handle = None
        self.thread_id = str(uuid.uuid4())

    def toggle_auto_approve(self) -> bool:
        """Toggle auto-approve and return new state."""
        self.auto_approve = not self.auto_approve
        return self.auto_approve


def get_default_coding_instructions() -> str:
    """Get the default coding agent instructions.

    These are the immutable base instructions that cannot be modified by the agent.
    Long-term memory (AGENTS.md) is handled separately by the middleware.
    """
    default_prompt_path = Path(__file__).parent / "default_agent_prompt.md"
    return default_prompt_path.read_text()


def _detect_provider(model_name: str) -> str | None:
    """Auto-detect provider from model name.

    Args:
        model_name: Model name to detect provider from

    Returns:
        Provider name (openai, anthropic, google, openai-compatible) or None if can't detect
    """
    model_lower = model_name.lower()
    if any(x in model_lower for x in ["gpt", "o1", "o3"]):
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "gemini" in model_lower:
        return "google"
    # Check for OpenAI-compatible API patterns - includes legacy patterns too for backward compatibility
    if any(
        x in model_lower
        for x in [
            "ollama",
            "local:",
            "llama",
            "mistral",
            "phi",
            "yi",
            "deepseek",
            "mixtral",
            "codellama",
            "wizardlm",
            "vicuna",
            "zephyr",
            "qwen",
            "devstral",
            "minimax",
        ]
    ):
        return "openai-compatible"
    return None


def create_model(model_name_override: str | None = None) -> BaseChatModel:
    """Create the appropriate model based on available API keys.

    Uses the global settings instance to determine which model to create.

    Args:
        model_name_override: Optional model name to use instead of environment variable

    Returns:
        ChatModel instance (OpenAI, Anthropic, or Google)

    Raises:
        SystemExit if no API key is configured or model provider can't be determined
    """
    from .model_selection import create_model_selection_chain, ModelFactory
    
    # Create the chain of model selection strategies
    chain = create_model_selection_chain(settings, console)
    
    # Execute the chain to get provider and model name
    result = chain.execute(model_name_override)
    if result is None:
        # This should not happen if the chain is properly implemented, but added for safety
        console.print("[bold red]Error:[/bold red] Could not determine model provider.")
        sys.exit(1)
    
    provider, model_name = result
    
    # Store model info in settings for display
    settings.model_name = model_name
    settings.model_provider = provider

    # Create and return the model using the factory
    return ModelFactory.create_model(provider, model_name, settings)
