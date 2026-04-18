"""CLI-specific tests."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gitlog.cli import app
from gitlog.config import GitlogConfig
from gitlog.core.models import Commit, CommitType, Tag

runner = CliRunner()


class TestNextVersionCommand:
    @patch("gitlog.cli.CommitClassifier")
    @patch("gitlog.cli.GitLogParser")
    @patch("gitlog.cli.load_settings")
    def test_next_version_json_output(
        self, mock_load_settings, mock_parser_cls, mock_classifier_cls
    ):
        mock_load_settings.return_value = GitlogConfig(
            llm_provider="",
            model="",
            paths=["src/gitlog"],
            commit_search_depth=15,
        )

        parser = MagicMock()
        parser.get_tags.return_value = [Tag(name="v1.2.3", sha="tag1234")]
        parser.get_commits.return_value = [
            Commit(sha="c1", message="feat: ship feature", author="dev", date="2024-01-01")
        ]
        mock_parser_cls.return_value = parser

        classifier = MagicMock()
        classifier.classify_all.return_value = [
            Commit(
                sha="c1",
                message="feat: ship feature",
                author="dev",
                date="2024-01-01",
                commit_type=CommitType.FEAT,
            )
        ]
        mock_classifier_cls.return_value = classifier

        result = runner.invoke(app, ["next-version", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.output.strip())
        assert payload["current_version"] == "v1.2.3"
        assert payload["next_version"] == "v1.3.0"
        parser.get_commits.assert_called_once()
        _, kwargs = parser.get_commits.call_args
        assert kwargs["paths"] == ["src/gitlog"]
        assert kwargs["max_count"] == 15

    @patch("gitlog.cli.CommitClassifier")
    @patch("gitlog.cli.GitLogParser")
    @patch("gitlog.cli.load_settings")
    def test_next_version_prerelease_and_hotfix(
        self, mock_load_settings, mock_parser_cls, mock_classifier_cls
    ):
        mock_load_settings.return_value = GitlogConfig(llm_provider="", model="")

        parser = MagicMock()
        parser.get_tags.return_value = [Tag(name="v2.4.5", sha="tag245")]
        parser.get_commits.return_value = [
            Commit(
                sha="c2",
                message="feat!: breaking hotfix",
                author="dev",
                date="2024-01-01",
            )
        ]
        mock_parser_cls.return_value = parser

        classifier = MagicMock()
        classifier.classify_all.return_value = [
            Commit(
                sha="c2",
                message="feat!: breaking hotfix",
                author="dev",
                date="2024-01-01",
                commit_type=CommitType.BREAKING,
            )
        ]
        mock_classifier_cls.return_value = classifier

        result = runner.invoke(app, ["next-version", "--json", "--hotfix", "--prerelease", "rc"])

        assert result.exit_code == 0
        payload = json.loads(result.output.strip())
        assert payload["bump"] == "patch"
        assert payload["next_version"] == "v2.4.6-rc.1"
