"""Model selection strategies using the Strategy and Chain of Responsibility patterns."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from langchain_core.language_models import BaseChatModel

if TYPE_CHECKING:
    from rich.console import Console

    from .config import Settings


class ModelSelectionStrategy(ABC):
    """Abstract base class for model selection strategies."""

    def __init__(self, settings: "Settings", console: "Console"):
        self.settings = settings
        self.console = console
        self.next_strategy: Optional["ModelSelectionStrategy"] = None

    def set_next(self, strategy: "ModelSelectionStrategy") -> "ModelSelectionStrategy":
        """Set the next strategy in the chain."""
        self.next_strategy = strategy
        return strategy

    def execute(self, model_name_override: Optional[str] = None) -> Optional[tuple[str, str]]:
        """Execute the strategy and return (provider, model_name) or None if not applicable."""
        result = self._try_select_model(model_name_override)
        if result is not None:
            return result
        if self.next_strategy:
            return self.next_strategy.execute(model_name_override)
        return None

    @abstractmethod
    def _try_select_model(self, model_name_override: Optional[str] = None) -> Optional[tuple[str, str]]:
        """Try to select a model, returning (provider, model_name) or None if not applicable."""


class ModelOverrideStrategy(ModelSelectionStrategy):
    """Strategy for handling model name overrides with explicit provider detection."""

    def _try_select_model(self, model_name_override: Optional[str] = None) -> Optional[tuple[str, str]]:
        if not model_name_override:
            return None

        # Use provided model, auto-detect provider
        provider = self._detect_provider(model_name_override)

        # If provider detection fails but OpenAI-compatible settings are configured and flagged for use,
        # use the OpenAI-compatible provider (this handles cases where users specify custom model names)
        if not provider and self.settings.has_openai_compatible and self._use_openai_compatible_flag():
            provider = "openai-compatible"
            # Use the model name as-is since it's meant for OpenAI-compatible API
        elif not provider:
            self._print_error_and_exit(model_name_override)

        # Check if API key for detected provider is available
        self._validate_provider_access(provider, model_name_override)

        return provider, model_name_override

    def _detect_provider(self, model_name: str) -> str | None:
        """Auto-detect provider from model name."""
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

    def _use_openai_compatible_flag(self) -> bool:
        """Check if OpenAI-compatible flag is set."""
        import os

        return bool(os.environ.get("USE_OPENAI_COMPATIBLE"))  # Fixed typo from "USE_OPENAI_COMPATIBLE" to "USE_OPENAI_COMPATIBLE"

    def _validate_provider_access(self, provider: str, model_name_override: str) -> None:
        """Validate that the provider has the required API keys."""
        if provider == "openai" and not self.settings.has_openai:
            self.console.print(f"[bold red]Error:[/bold red] Model '{model_name_override}' requires OPENAI_API_KEY")
            import sys

            sys.exit(1)
        elif provider == "anthropic" and not self.settings.has_anthropic:
            self.console.print(f"[bold red]Error:[/bold red] Model '{model_name_override}' requires ANTHROPIC_API_KEY")
            import sys

            sys.exit(1)
        elif provider == "google" and not self.settings.has_google:
            self.console.print(f"[bold red]Error:[/bold red] Model '{model_name_override}' requires GOOGLE_API_KEY")
            import sys

            sys.exit(1)
        elif provider == "openai-compatible" and not self.settings.has_openai_compatible:
            self.console.print(f"[bold red]Error:[/bold red] Model '{model_name_override}' requires OPENAI_COMPATIBLE_URL to be set")
            self.console.print("\nPlease set the OPENAI_COMPATIBLE_URL environment variable:")
            self.console.print("  export OPENAI_COMPATIBLE_URL=http://localhost:11434/v1  # Ollama example")
            self.console.print("  export OPENAI_COMPATIBLE_URL=http://localhost:8000/v1    # LocalAI/vLLM example")
            import sys

            sys.exit(1)

    def _print_error_and_exit(self, model_name_override: str) -> None:
        """Print error message and exit when provider detection fails."""
        self.console.print(f"[bold red]Error:[/bold red] Could not detect provider from model name: {model_name_override}")
        self.console.print("\nSupported model name patterns:")
        self.console.print("  - OpenAI: gpt-*, o1-*, o3-*")
        self.console.print("  - Anthropic: claude-*")
        self.console.print("  - Google: gemini-*")
        self.console.print("  - OpenAI-compatible: ollama:<model>, local:<model>, llama*, mistral*, etc. (when OpenAI-compatible API is configured)")
        self.console.print("\nAlternatively, configure OpenAI-compatible API with --openai-compatible-url and --model")
        import sys

        sys.exit(1)


class EnvironmentBasedStrategy(ModelSelectionStrategy):
    """Strategy for selecting models based on environment variables and API key availability."""

    def _try_select_model(self, model_name_override: Optional[str] = None) -> Optional[tuple[str, str]]:
        if model_name_override:
            return None  # Not our responsibility if there's an override

        # Use environment variable defaults, detect provider by API key priority
        # Check for OpenAI-compatible API first if configured
        import os

        if self.settings.has_openai_compatible and os.environ.get("USE_OPENAI_COMPATIBLE"):
            provider = "openai-compatible"
            # If no specific model was provided via model_name_override, use the default
            model_name = os.environ.get("OPENAI_COMPATIBLE_MODEL", "llama3")  # Default OpenAI-compatible model
        elif self.settings.has_openai:
            provider = "openai"
            model_name = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        elif self.settings.has_anthropic:
            provider = "anthropic"
            model_name = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        elif self.settings.has_google:
            provider = "google"
            model_name = os.environ.get("GOOGLE_MODEL", "gemini-3-pro-preview")
        elif self.settings.has_openai_compatible:
            provider = "openai-compatible"
            model_name = os.environ.get("OPENAI_COMPATIBLE_MODEL", "llama3")  # Default OpenAI-compatible model
        else:
            self._print_no_api_key_error()
            return None  # This won't return due to sys.exit

        return provider, model_name

    def _print_no_api_key_error(self) -> None:
        """Print error message when no API keys are configured."""
        self.console.print("[bold red]Error:[/bold red] No API key configured.")
        self.console.print("\nPlease set one of the following environment variables:")
        self.console.print("  - OPENAI_API_KEY     (for OpenAI models like gpt-5-mini)")
        self.console.print("  - ANTHROPIC_API_KEY  (for Claude models)")
        self.console.print("  - GOOGLE_API_KEY     (for Google Gemini models)")
        self.console.print("  - OPENAI_COMPATIBLE_URL (for OpenAI-compatible APIs like Ollama, LocalAI)")
        self.console.print("  - OPENAI_COMPATIBLE_API_KEY  (optional, defaults to 'sk-openai-compatible')")
        self.console.print("\nExamples:")
        self.console.print("  export OPENAI_API_KEY=your_api_key_here")
        self.console.print("  export OPENAI_COMPATIBLE_URL=http://localhost:11434/v1")
        self.console.print("\nOr add them to your .env file.")
        import sys

        sys.exit(1)


class ModelFactory:
    """Factory to create the appropriate model based on the selected provider."""

    @staticmethod
    def create_model(provider: str, model_name: str, settings: "Settings") -> BaseChatModel:
        """Create a model instance based on provider and model name."""
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=model_name)
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model_name=model_name,
                max_tokens=20_000,  # type: ignore[arg-type]
            )
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0,
                max_tokens=None,
            )
        elif provider == "openai-compatible":
            from langchain_openai import ChatOpenAI

            # Use the OpenAI-compatible configuration
            # For OpenAI-compatible providers, just use the model name directly (remove prefixes if present)
            clean_model_name = model_name.replace("openai-compatible:", "").replace("local:", "")
            return ChatOpenAI(
                model=clean_model_name,
                base_url=settings.openai_compatible_url,
                api_key=settings.openai_compatible_api_key,
                temperature=0.7,  # Default temperature for OpenAI-compatible models
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")


def create_model_selection_chain(settings: "Settings", console: "Console") -> ModelSelectionStrategy:
    """Create a chain of model selection strategies."""
    override_strategy = ModelOverrideStrategy(settings, console)
    env_strategy = EnvironmentBasedStrategy(settings, console)

    override_strategy.set_next(env_strategy)

    return override_strategy
