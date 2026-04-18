"""Tests for the GitLogParser."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from gitlog.core.git import GitLogParser
from gitlog.core.models import Commit


class TestGitLogParser:
    """Tests for GitLogParser using mocked git repo."""

    def _make_mock_commit(self, sha, message, author="Test", committed_date=0):
        mc = MagicMock()
        mc.hexsha = sha
        mc.message = message
        mc.author.name = author
        mc.committed_date = committed_date
        mc.stats.total = {"insertions": 1, "deletions": 0, "lines": 1}
        return mc

    @patch("gitlog.core.git.Repo")
    def test_get_commits_returns_list(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.iter_commits.return_value = [
            self._make_mock_commit("abc1234", "feat: initial commit"),
            self._make_mock_commit("def5678", "fix: patch bug"),
        ]
        mock_repo.tags = []

        parser = GitLogParser()
        commits = parser.get_commits()

        assert len(commits) == 2
        assert all(isinstance(c, Commit) for c in commits)
        assert commits[0].sha == "abc1234"
        assert commits[1].sha == "def5678"

    @patch("gitlog.core.git.Repo")
    def test_get_commits_with_since(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.iter_commits.return_value = []
        mock_repo.tags = []

        parser = GitLogParser()
        commits = parser.get_commits(since="v1.0.0")
        assert commits == []

    @patch("gitlog.core.git.Repo")
    def test_get_commits_passes_paths_and_max_count(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.iter_commits.return_value = []
        mock_repo.tags = []

        parser = GitLogParser()
        commits = parser.get_commits(since="v1.0.0", paths=["src/gitlog"], max_count=5)

        assert commits == []
        args, kwargs = mock_repo.iter_commits.call_args
        assert args[0] == "v1.0.0..HEAD"
        assert kwargs["paths"] == ["src/gitlog"]
        assert kwargs["max_count"] == 5

    @patch("gitlog.core.git.Repo")
    def test_pr_ref_parsed(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.iter_commits.return_value = [
            self._make_mock_commit("aaa0001", "feat: new thing\n\nCloses #42"),
        ]
        mock_repo.tags = []

        parser = GitLogParser()
        commits = parser.get_commits()
        assert "42" in commits[0].issue_refs
