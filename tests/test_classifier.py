"""Tests for the commit classification engine."""
from __future__ import annotations

from unittest.mock import MagicMock

from gitlog.config import GitlogConfig
from gitlog.core.classifier import CommitClassifier, RuleBasedClassifier
from gitlog.core.models import Commit, CommitType


class TestRuleBasedClassifier:
    """Unit tests for the rule-based classifier layer."""

    def setup_method(self):
        self.clf = RuleBasedClassifier()

    def _commit(self, message: str, body: str = "") -> Commit:
        return Commit(sha="abc1234", message=message, author="test", date="2024-01-01", body=body)

    def test_feat_prefix(self):
        assert self.clf.classify(self._commit("feat: add OAuth login")) == CommitType.FEAT

    def test_fix_prefix(self):
        assert self.clf.classify(self._commit("fix: correct null pointer")) == CommitType.FIX

    def test_perf_prefix(self):
        assert self.clf.classify(self._commit("perf: use index scan")) == CommitType.PERF

    def test_chore_prefix(self):
        assert self.clf.classify(self._commit("chore(deps): bump library")) == CommitType.CHORE

    def test_breaking_exclamation(self):
        assert self.clf.classify(self._commit("feat!: redesign API")) == CommitType.BREAKING

    def test_breaking_footer(self):
        result = self.clf.classify(
            self._commit("feat: new API", body="BREAKING CHANGE: removes v1 endpoints")
        )
        assert result == CommitType.BREAKING

    def test_docs_prefix(self):
        assert self.clf.classify(self._commit("docs: update README")) == CommitType.DOCS

    def test_non_conventional_returns_none(self):
        assert self.clf.classify(self._commit("Fixed the login bug")) is None

    def test_case_insensitive(self):
        assert self.clf.classify(self._commit("FEAT: upper case")) == CommitType.FEAT

    def test_refactor_prefix(self):
        assert self.clf.classify(self._commit("refactor: extract helper")) == CommitType.REFACTOR


class TestCommitClassifier:
    """Integration tests for CommitClassifier (rule-only, no LLM)."""

    def test_classify_all_conventional(self, default_config, sample_conventional_commits):
        clf = CommitClassifier(default_config)
        result = clf.classify_all(sample_conventional_commits)
        types = [c.commit_type for c in result]
        assert CommitType.FEAT in types
        assert CommitType.FIX in types
        assert CommitType.BREAKING in types

    def test_non_conventional_defaults_to_misc_without_llm(self, default_config):
        clf = CommitClassifier(default_config)
        commits = [
            Commit(sha="x", message="random message", author="a", date="2024-01-01")
        ]
        result = clf.classify_all(commits)
        assert result[0].commit_type == CommitType.MISC

    def test_returns_same_length(self, default_config, sample_all_commits):
        clf = CommitClassifier(default_config)
        result = clf.classify_all(sample_all_commits)
        assert len(result) == len(sample_all_commits)

    def test_uses_configured_provider(self, monkeypatch):
        mock_provider = MagicMock()
        mock_provider.complete_json.return_value = {"types": ["fix"]}
        monkeypatch.setattr(
            "gitlog.core.classifier.create_provider",
            lambda _provider, _model: mock_provider,
        )

        cfg = GitlogConfig(llm_provider="openai", model="gpt-4o-mini")
        clf = CommitClassifier(cfg)
        commits = [Commit(sha="x", message="random message", author="a", date="2024-01-01")]
        result = clf.classify_all(commits)

        assert result[0].commit_type == CommitType.FIX
        mock_provider.complete_json.assert_called_once()

    def test_uses_custom_classify_prompt(self, monkeypatch):
        seen_system_prompts: list[str] = []

        class _Provider:
            def complete_json(self, system: str, user: str):
                seen_system_prompts.append(system)
                return {"types": ["chore"]}

        monkeypatch.setattr(
            "gitlog.core.classifier.create_provider",
            lambda _provider, _model: _Provider(),
        )

        cfg = GitlogConfig(
            llm_provider="openai",
            model="gpt-4o-mini",
            prompts={"classify_system": "CUSTOM SYSTEM PROMPT"},
        )
        clf = CommitClassifier(cfg)
        commits = [Commit(sha="x", message="random message", author="a", date="2024-01-01")]
        result = clf.classify_all(commits)

        assert result[0].commit_type == CommitType.CHORE
        assert seen_system_prompts and seen_system_prompts[0].startswith(
            "CUSTOM SYSTEM PROMPT"
        )
