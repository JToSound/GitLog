"""Configuration loading tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from gitlog.config import GitlogConfig, load_settings


def test_load_settings_env_overrides_file(tmp_path, monkeypatch):
    cfg = tmp_path / ".gitlog.toml"
    cfg.write_text(
        "\n".join(
            [
                "[gitlog]",
                'llm_provider = "openai"',
                'model = "gpt-4o-mini"',
                'language = "en"',
                "commit_search_depth = 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GITLOG_LANGUAGE", "zh-TW")

    settings = load_settings(tmp_path)

    assert settings.language == "zh-TW"
    assert settings.llm_provider == "openai"


def test_invalid_llm_provider_raises():
    with pytest.raises(ValidationError):
        GitlogConfig(llm_provider="invalid-provider")
