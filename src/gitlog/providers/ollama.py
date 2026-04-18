"""Ollama local provider via litellm."""
from __future__ import annotations

import json
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from gitlog.exceptions import LLMError
from gitlog.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    """Provider that wraps locally-running Ollama models through litellm."""

    def __init__(
        self,
        model: str = "ollama/llama3",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._temperature = temperature

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def complete(self, system: str, user: str) -> str:
        """Call local Ollama and return raw text.

        Args:
            system: System prompt.
            user: User prompt.

        Returns:
            Model response as plain text.

        Raises:
            LLMError: On connection or API failure.
        """
        try:
            import litellm

            resp = litellm.completion(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                api_base=self._base_url,
                temperature=self._temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(str(exc)) from exc

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        """Call Ollama and attempt to parse JSON from the response.

        Args:
            system: System prompt (should instruct JSON output).
            user: User prompt.

        Returns:
            Parsed JSON dict.

        Raises:
            LLMError: On API or parse failure.
        """
        raw = self.complete(
            system + "\nReturn ONLY valid JSON. No markdown fences.", user
        )
        # Strip potential markdown fences
        stripped = raw.strip()
        if stripped.startswith("```json"):
            stripped = stripped[7:].strip()
        elif stripped.startswith("```"):
            stripped = stripped[3:].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
        try:
            data = json.loads(stripped)
            if not isinstance(data, dict):
                raise LLMError("Model did not return a JSON object.")
            return data
        except json.JSONDecodeError as exc:
            raise LLMError(f"JSON parse error: {exc}\nRaw: {raw[:200]}") from exc
