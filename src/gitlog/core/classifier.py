"""Commit classification engine with rule-based and LLM-powered layers."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from gitlog.core.models import Commit, CommitType
from gitlog.providers import create_provider

if TYPE_CHECKING:
    from gitlog.config import GitlogConfig
    from gitlog.providers.base import BaseProvider

# ---------------------------------------------------------------------------
# Regex patterns for Conventional Commits
# ---------------------------------------------------------------------------
_CC_PATTERN = re.compile(
    r"^(?P<type>feat|fix|perf|refactor|docs|style|test|chore|ci|build|revert)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s+(?P<desc>.+)$",
    re.IGNORECASE,
)
_BREAKING_FOOTER = re.compile(r"BREAKING[- ]CHANGE:", re.IGNORECASE)

_TYPE_MAP: dict[str, CommitType] = {
    "feat": CommitType.FEAT,
    "fix": CommitType.FIX,
    "perf": CommitType.PERF,
    "refactor": CommitType.REFACTOR,
    "docs": CommitType.DOCS,
    "style": CommitType.CHORE,
    "test": CommitType.CHORE,
    "chore": CommitType.CHORE,
    "ci": CommitType.CHORE,
    "build": CommitType.CHORE,
    "revert": CommitType.FIX,
}


class RuleBasedClassifier:
    """Layer-1: zero-cost rule-engine classifier."""

    def classify(self, commit: Commit) -> CommitType | None:
        """Return CommitType if the commit matches a Conventional Commits pattern.

        Args:
            commit: The commit to classify.

        Returns:
            CommitType if matched, otherwise None.
        """
        msg = commit.message.strip()

        # BREAKING CHANGE footer takes precedence
        full_text = msg + "\n" + (commit.body or "")
        if _BREAKING_FOOTER.search(full_text):
            return CommitType.BREAKING

        m = _CC_PATTERN.match(msg)
        if m:
            if m.group("breaking"):
                return CommitType.BREAKING
            return _TYPE_MAP.get(m.group("type").lower(), CommitType.MISC)

        return None


class LLMClassifier:
    """Layer-2: batched LLM classifier for non-conventional commits."""

    _DEFAULT_CHUNK_SIZE = 40  # max commits per LLM request

    def __init__(self, config: GitlogConfig) -> None:
        self._config = config
        self._chunk_size = (
            config.llm_batch_size if config.llm_batch_size > 0 else self._DEFAULT_CHUNK_SIZE
        )
        self._provider: BaseProvider | None = None
        if config.llm_provider:
            self._provider = create_provider(config.llm_provider, config.model)

    def classify_batch(self, commits: list[Commit]) -> list[CommitType]:
        """Classify a list of commits using the LLM in batches.

        Args:
            commits: Commits that could not be classified by the rule engine.

        Returns:
            List of CommitType values in the same order as the input.
        """
        results: list[CommitType] = []
        for i in range(0, len(commits), self._chunk_size):
            chunk = commits[i : i + self._chunk_size]
            results.extend(self._classify_chunk(chunk))
        return results

    def _classify_chunk(self, commits: list[Commit]) -> list[CommitType]:
        """Classify a single chunk of commits."""
        if self._provider is None:
            return [CommitType.MISC] * len(commits)

        numbered = "\n".join(
            f"{idx + 1}. {c.message[:200]}" for idx, c in enumerate(commits)
        )
        default_system_prompt = (
            "You are a changelog classifier. "
            "Classify each git commit into EXACTLY one of: "
            "feat, fix, perf, refactor, docs, chore, breaking.\n"
            "Return a JSON object with key 'types' containing an array matching the input order.\n"
            "Be concise. Do not explain."
        )
        system_prompt = self._config.prompts.classify_system.strip() or default_system_prompt
        if self._config.project_description:
            system_prompt += f"\nProject context: {self._config.project_description}"

        user_prompt = (
            f"Classify these {len(commits)} commits:\n{numbered}\n\n"
            'RESPONSE FORMAT: {"types": ["feat", "fix", ...]}'
        )

        try:
            data = self._provider.complete_json(system_prompt, user_prompt)
            types_raw: list[str] = data.get("types", [])
            mapping = {
                "feat": CommitType.FEAT,
                "fix": CommitType.FIX,
                "perf": CommitType.PERF,
                "refactor": CommitType.REFACTOR,
                "docs": CommitType.DOCS,
                "chore": CommitType.CHORE,
                "breaking": CommitType.BREAKING,
            }
            return [
                mapping.get(t.lower(), CommitType.MISC)
                for t in types_raw[: len(commits)]
            ]
        except Exception:  # noqa: BLE001 – fallback, never crash
            return [CommitType.MISC] * len(commits)


class CommitClassifier:
    """Orchestrates rule-based (Layer 1) + LLM (Layer 2) classification."""

    def __init__(self, config: GitlogConfig) -> None:
        self._rule = RuleBasedClassifier()
        self._llm = LLMClassifier(config)
        self._use_llm = bool(config.llm_provider)

    def classify_all(self, commits: list[Commit]) -> list[Commit]:
        """Classify a list of commits in-place, returning annotated commits.

        Args:
            commits: Raw commits to classify.

        Returns:
            The same commits with `commit_type` populated.
        """
        unclassified_idx: list[int] = []
        unclassified: list[Commit] = []

        for idx, commit in enumerate(commits):
            ct = self._rule.classify(commit)
            if ct is not None:
                commits[idx] = commit.model_copy(update={"commit_type": ct})
            else:
                unclassified_idx.append(idx)
                unclassified.append(commit)

        if unclassified and self._use_llm:
            llm_types = self._llm.classify_batch(unclassified)
            for idx, ct in zip(unclassified_idx, llm_types, strict=False):
                commits[idx] = commits[idx].model_copy(update={"commit_type": ct})
        else:
            for idx in unclassified_idx:
                commits[idx] = commits[idx].model_copy(
                    update={"commit_type": CommitType.MISC}
                )

        return commits
