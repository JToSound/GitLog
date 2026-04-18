"""Anthropic provider via litellm."""
from __future__ import annotations

import json
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from gitlog.exceptions import LLMError
from gitlog.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Provider that wraps Anthropic Claude models through litellm."""

    def __init__(
        self, model: str = "claude-3-haiku-20240307", temperature: float = 0.0
    ) -> None:
        self._model = model
        self._temperature = temperature

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def complete(self, system: str, user: str) -> str:
        """Call Anthropic and return raw text.

        Args:
            system: System prompt.
            user: User prompt.

        Returns:
            Model response as plain text.

        Raises:
            LLMError: On API failure.
        """
        try:
            import litellm

            resp = litellm.completion(
                model=f"anthropic/{self._model}",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=self._temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(str(exc)) from exc

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        """Call Anthropic and parse JSON from the response.

        Args:
            system: System prompt (should instruct JSON output).
            user: User prompt.

        Returns:
            Parsed JSON dict.

        Raises:
            LLMError: On API or parse failure.
        """
        raw = self.complete(
            system + "\nRespond ONLY with valid JSON.", user
        )
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise LLMError("Model did not return a JSON object.")
            return data
        except json.JSONDecodeError as exc:
            raise LLMError(f"JSON parse error: {exc}\nRaw: {raw[:200]}") from exc
