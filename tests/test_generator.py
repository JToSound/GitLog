"""Tests for the ChangelogGenerator."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from gitlog.core.generator import ChangelogGenerator, _deduplicate
from gitlog.core.models import Commit, Tag


class TestDeduplicate:
    """Unit tests for the internal deduplication helper."""

    def test_removes_near_duplicates(self):
        commits = [
            Commit(sha="a", message="fix login bug", author="x", date="d"),
            Commit(sha="b", message="fix login bUg", author="x", date="d"),
        ]
        result = _deduplicate(commits, threshold=5)
        assert len(result) == 1

    def test_keeps_distinct_commits(self):
        commits = [
            Commit(sha="a", message="feat: add dark mode", author="x", date="d"),
            Commit(sha="b", message="fix: correct token expiry", author="x", date="d"),
        ]
        result = _deduplicate(commits, threshold=5)
        assert len(result) == 2

    def test_empty_list(self):
        assert _deduplicate([]) == []


class TestChangelogGenerator:
    """Integration tests for ChangelogGenerator."""

    @patch("gitlog.core.generator.GitLogParser")
    @patch("gitlog.core.generator.CommitClassifier")
    def test_generate_unreleased(
        self,
        mock_clf_cls,
        mock_parser_cls,
        default_config,
        sample_conventional_commits,
    ):
        mock_parser = MagicMock()
        mock_parser_cls.return_value = mock_parser
        mock_parser.get_unreleased_commits.return_value = sample_conventional_commits

        mock_clf = MagicMock()
        mock_clf_cls.return_value = mock_clf
        mock_clf.classify_all.side_effect = lambda c: c  # passthrough

        gen = ChangelogGenerator(default_config)
        entry = gen.generate_unreleased()

        assert entry.version == "Unreleased"

    @patch("gitlog.core.generator.GitLogParser")
    @patch("gitlog.core.generator.CommitClassifier")
    def test_generate_full(
        self,
        mock_clf_cls,
        mock_parser_cls,
        default_config,
        sample_conventional_commits,
    ):
        mock_parser = MagicMock()
        mock_parser_cls.return_value = mock_parser
        mock_parser.get_tags.return_value = []
        mock_parser.get_commits.return_value = sample_conventional_commits

        mock_clf = MagicMock()
        mock_clf_cls.return_value = mock_clf
        mock_clf.classify_all.side_effect = lambda c: c

        gen = ChangelogGenerator(default_config)
        changelog = gen.generate()

        assert len(changelog.entries) >= 1

    def test_partitions_entries_by_tag_boundaries(self, default_config):
        gen = ChangelogGenerator(default_config)
        gen._parser = MagicMock()
        gen._parser.get_tags.return_value = [
            Tag(name="v2.0.0", sha="t2000"),
            Tag(name="v1.0.0", sha="t1000"),
        ]

        commits = [
            Commit(sha="u0001", message="fix: unreleased patch", author="a", date="2024-01-05"),
            Commit(sha="t2000", message="feat: shipped in v2", author="a", date="2024-01-04"),
            Commit(sha="b0001", message="fix: included in v2", author="a", date="2024-01-03"),
            Commit(sha="t1000", message="feat: shipped in v1", author="a", date="2024-01-02"),
        ]

        changelog = gen.generate(commits=commits)
        versions = [entry.version for entry in changelog.entries]

        assert versions == ["Unreleased", "v2.0.0", "v1.0.0"]
