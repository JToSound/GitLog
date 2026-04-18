"""LLM provider factory and exports."""
from __future__ import annotations

from gitlog.exceptions import ConfigError
from gitlog.providers.anthropic import AnthropicProvider
from gitlog.providers.base import BaseProvider
from gitlog.providers.ollama import OllamaProvider
from gitlog.providers.openai import OpenAIProvider


def create_provider(provider: str, model: str) -> BaseProvider:
    """Create a provider adapter from config values.

    Args:
        provider: Provider name from config (`openai`, `anthropic`, `ollama`, `gemini`).
        model: Model identifier.

    Returns:
        Concrete provider adapter.

    Raises:
        ConfigError: If provider value is unsupported.
    """
    normalized = provider.strip().lower()
    if normalized == "openai":
        return OpenAIProvider(model=model)
    if normalized == "anthropic":
        return AnthropicProvider(model=model)
    if normalized == "ollama":
        return OllamaProvider(model=model)
    if normalized == "gemini":
        # Gemini works via LiteLLM with model IDs like `gemini/gemini-1.5-flash`.
        return OpenAIProvider(model=model or "gemini/gemini-1.5-flash")
    raise ConfigError(
        f"Unsupported llm_provider: {provider}",
        hint="Use one of: openai, anthropic, ollama, gemini, or empty string.",
    )
