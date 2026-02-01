"""Language detection strategies using the Strategy pattern to replace if/elif chains."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional


class LanguageDetectionStrategy(ABC):
    """Abstract base class for language detection strategies."""
    
    def __init__(self, next_strategy: 'LanguageDetectionStrategy' = None):
        self.next_strategy = next_strategy
    
    def set_next(self, strategy: 'LanguageDetectionStrategy') -> 'LanguageDetectionStrategy':
        """Set the next strategy in the chain."""
        self.next_strategy = strategy
        return strategy
    
    def detect(self, cwd: Path) -> Optional[str]:
        """Detect language, returning language name or None if not detected."""
        result = self._detect_language(cwd)
        if result is not None:
            return result
        elif self.next_strategy:
            return self.next_strategy.detect(cwd)
        else:
            return None
    
    @abstractmethod
    def _detect_language(self, cwd: Path) -> Optional[str]:
        """Detect language for this specific strategy."""
        pass


class PythonDetectionStrategy(LanguageDetectionStrategy):
    """Detect Python projects."""
    
    def _detect_language(self, cwd: Path) -> Optional[str]:
        if (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists():
            return "python"
        return None


class JavaScriptDetectionStrategy(LanguageDetectionStrategy):
    """Detect JavaScript/TypeScript projects."""
    
    def _detect_language(self, cwd: Path) -> Optional[str]:
        if (cwd / "package.json").exists():
            return "javascript/typescript"
        return None


class RustDetectionStrategy(LanguageDetectionStrategy):
    """Detect Rust projects."""
    
    def _detect_language(self, cwd: Path) -> Optional[str]:
        if (cwd / "Cargo.toml").exists():
            return "rust"
        return None


class GoDetectionStrategy(LanguageDetectionStrategy):
    """Detect Go projects."""
    
    def _detect_language(self, cwd: Path) -> Optional[str]:
        if (cwd / "go.mod").exists():
            return "go"
        return None


class JavaDetectionStrategy(LanguageDetectionStrategy):
    """Detect Java projects."""
    
    def _detect_language(self, cwd: Path) -> Optional[str]:
        if (cwd / "pom.xml").exists() or (cwd / "build.gradle").exists():
            return "java"
        return None


def create_language_detection_chain() -> LanguageDetectionStrategy:
    """Create a chain of language detection strategies."""
    python_strategy = PythonDetectionStrategy()
    js_strategy = JavaScriptDetectionStrategy()
    rust_strategy = RustDetectionStrategy()
    go_strategy = GoDetectionStrategy()
    java_strategy = JavaDetectionStrategy()
    
    python_strategy.set_next(js_strategy)
    js_strategy.set_next(rust_strategy)
    rust_strategy.set_next(go_strategy)
    go_strategy.set_next(java_strategy)
    
    return python_strategy


def detect_language(cwd: Path) -> str:
    """Detect the primary language of a project directory."""
    chain = create_language_detection_chain()
    result = chain.detect(cwd)
    return result or "unknown"