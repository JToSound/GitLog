"""Configuration management for gitlog using pydantic-settings."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PromptsConfig(BaseSettings):
    """Custom prompt overrides."""

    model_config = SettingsConfigDict(extra="ignore")

    classify_system: str = ""
    summarize_system: str = ""


class GitHubConfig(BaseSettings):
    """GitHub integration settings."""

    model_config = SettingsConfigDict(extra="ignore")

    repo: str = ""  # owner/repo


class GitlogConfig(BaseSettings):
    """Main gitlog configuration.

    Can be loaded from .gitlog.toml or environment variables (GITLOG_ prefix).
    """

    model_config = SettingsConfigDict(
        env_prefix="GITLOG_",
        extra="ignore",
    )

    llm_provider: str = "openai"
    model: str = "gpt-4o-mini"
    language: str = "en"
    format: str = "markdown"
    output_file: str = "CHANGELOG.md"
    project_description: str = ""
    project_name: str = ""
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["^chore\\(deps\\)", "^Merge branch", "^Merge pull request"]
    )
    group_by_scope: bool = True
    max_commits_per_group: int = 20
    paths: list[str] = Field(default_factory=list)
    commit_search_depth: int = 0
    llm_batch_size: int = 40

    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code."""
        allowed = {"en", "zh-TW", "zh-CN", "ja"}
        if v not in allowed:
            raise ValueError(f"language must be one of {allowed}")
        return v

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate provider selection (empty string disables LLM fallback)."""
        allowed = {"", "openai", "anthropic", "ollama", "gemini"}
        if v not in allowed:
            raise ValueError(f"llm_provider must be one of {allowed}")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate output format."""
        allowed = {"markdown", "json", "html", "twitter"}
        if v not in allowed:
            raise ValueError(f"format must be one of {allowed}")
        return v

    @field_validator("commit_search_depth", "llm_batch_size")
    @classmethod
    def validate_non_negative_ints(cls, v: int) -> int:
        """Validate positive-ish integer settings (0 means unlimited for depth)."""
        if v < 0:
            raise ValueError("value must be >= 0")
        return v


def load_settings(repo_path: Path | None = None) -> GitlogConfig:
    """Load settings from .gitlog.toml and environment variables.

    Args:
        repo_path: Path to the repository root. Defaults to cwd.

    Returns:
        Populated GitlogConfig instance.
    """
    base = repo_path or Path.cwd()
    toml_path = base / ".gitlog.toml"

    if toml_path.exists():
        import tomllib

        with toml_path.open("rb") as f:
            raw: dict[str, Any] = tomllib.load(f)

        section = raw.get("gitlog", {})
        prompts_data = section.pop("prompts", {})
        github_data = section.pop("github", {})

        file_config = GitlogConfig(
            **section,
            prompts=PromptsConfig(**prompts_data),
            github=GitHubConfig(**github_data),
        )
        env_config = GitlogConfig()

        merged = file_config.model_dump()

        env_field_map = {
            "llm_provider": "GITLOG_LLM_PROVIDER",
            "model": "GITLOG_MODEL",
            "language": "GITLOG_LANGUAGE",
            "format": "GITLOG_FORMAT",
            "output_file": "GITLOG_OUTPUT_FILE",
            "project_description": "GITLOG_PROJECT_DESCRIPTION",
            "project_name": "GITLOG_PROJECT_NAME",
            "exclude_patterns": "GITLOG_EXCLUDE_PATTERNS",
            "group_by_scope": "GITLOG_GROUP_BY_SCOPE",
            "max_commits_per_group": "GITLOG_MAX_COMMITS_PER_GROUP",
            "paths": "GITLOG_PATHS",
            "commit_search_depth": "GITLOG_COMMIT_SEARCH_DEPTH",
            "llm_batch_size": "GITLOG_LLM_BATCH_SIZE",
        }
        for field, env_key in env_field_map.items():
            if env_key in os.environ:
                merged[field] = getattr(env_config, field)

        if "GITLOG_PROMPTS__CLASSIFY_SYSTEM" in os.environ:
            merged["prompts"]["classify_system"] = env_config.prompts.classify_system
        if "GITLOG_PROMPTS__SUMMARIZE_SYSTEM" in os.environ:
            merged["prompts"]["summarize_system"] = env_config.prompts.summarize_system
        if "GITLOG_GITHUB__REPO" in os.environ:
            merged["github"]["repo"] = env_config.github.repo

        return GitlogConfig(**merged)

    return GitlogConfig()


# Alias for backward compat
GitlogSettings = GitlogConfig
