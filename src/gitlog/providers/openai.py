"""OpenAI provider via litellm."""
from __future__ import annotations

import json
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from gitlog.exceptions import LLMError
from gitlog.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Provider that wraps OpenAI-compatible models through litellm."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0) -> None:
        self._model = model
        self._temperature = temperature

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def complete(self, system: str, user: str) -> str:
        """Call OpenAI and return raw text.

        Args:
            system: System prompt.
            user: User prompt.

        Returns:
            Model response as plain text.

        Raises:
            LLMError: If the call fails after retries.
        """
        try:
            import litellm

            resp = litellm.completion(
                model=self._model,
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
        """Call OpenAI with JSON mode enabled.

        Args:
            system: System prompt.
            user: User prompt.

        Returns:
            Parsed JSON dict.

        Raises:
            LLMError: If the call or JSON parsing fails.
        """
        try:
            import litellm

            resp = litellm.completion(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=self._temperature,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            if not isinstance(data, dict):
                raise LLMError("Model did not return a JSON object.")
            return data
        except Exception as exc:
            raise LLMError(str(exc)) from exc
