"""Abstract base class for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Common interface that all LLM provider adapters must implement."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Send a system + user message and return the model response.

        Args:
            system: The system-role message.
            user: The user-role message.

        Returns:
            The model's text response.
        """

    @abstractmethod
    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        """Like `complete`, but parse and return a JSON dict.

        Args:
            system: The system-role message.
            user: The user-role message.

        Returns:
            Parsed JSON dict from the model response.
        """
