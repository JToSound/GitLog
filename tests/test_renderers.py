"""Tests for all renderers."""
from __future__ import annotations

import json

from gitlog.core.models import Changelog, ChangelogEntry, CommitType
from gitlog.renderers.html import HtmlRenderer
from gitlog.renderers.json import JsonRenderer
from gitlog.renderers.markdown import MarkdownRenderer
from gitlog.renderers.twitter import TwitterRenderer
from tests.fixtures.sample_commits import CONVENTIONAL_COMMITS


def _make_entry() -> ChangelogEntry:
    feat_commits = [
        c.model_copy(update={"scope": "ui"})
        for c in CONVENTIONAL_COMMITS
        if c.commit_type == CommitType.FEAT
    ]
    fix_commits = [
        c.model_copy(update={"scope": "auth"})
        for c in CONVENTIONAL_COMMITS
        if c.commit_type == CommitType.FIX
    ]
    return ChangelogEntry(
        version="v1.2.0",
        date="2024-01-15",
        groups={
            CommitType.FEAT: feat_commits,
            CommitType.FIX: fix_commits,
        },
    )


def _make_changelog() -> Changelog:
    return Changelog(entries=[_make_entry()])


class TestMarkdownRenderer:
    def test_renders_version_header(self):
        renderer = MarkdownRenderer()
        output = renderer.render(_make_changelog())
        assert "v1.2.0" in output

    def test_renders_feat_section(self):
        renderer = MarkdownRenderer()
        output = renderer.render(_make_changelog())
        assert "feat" in output.lower() or "feature" in output.lower()

    def test_sha_link_with_github_repo(self):
        renderer = MarkdownRenderer(github_repo="owner/repo")
        output = renderer.render(_make_changelog())
        assert "github.com/owner/repo/commit" in output

    def test_sha_link_without_repo(self):
        renderer = MarkdownRenderer()
        output = renderer.render(_make_changelog())
        # SHA appears as inline code
        assert "`" in output

    def test_empty_changelog(self):
        output = MarkdownRenderer().render(Changelog(entries=[]))
        assert "Changelog" in output

    def test_localized_header_zh_tw(self):
        output = MarkdownRenderer(language="zh-TW").render(_make_changelog())
        assert "變更日誌" in output

    def test_group_by_scope_shows_scope_heading(self):
        output = MarkdownRenderer(group_by_scope=True).render(_make_changelog())
        assert "Scope:" in output and "`auth`" in output


class TestHtmlRenderer:
    def test_localized_labels_zh_tw(self):
        output = HtmlRenderer(language="zh-TW").render(_make_changelog())
        assert "切換深色模式" in output

    def test_group_by_scope_shows_scope_heading(self):
        output = HtmlRenderer(group_by_scope=True).render(_make_changelog())
        assert "Scope:" in output and "<code>auth</code>" in output


class TestJsonRenderer:
    def test_valid_json(self):
        renderer = JsonRenderer()
        output = renderer.render(_make_changelog())
        data = json.loads(output)
        assert "entries" in data

    def test_entry_structure(self):
        renderer = JsonRenderer()
        data = json.loads(renderer.render(_make_changelog()))
        entry = data["entries"][0]
        assert entry["version"] == "v1.2.0"
        assert entry["date"] == "2024-01-15"
        assert "groups" in entry

    def test_commit_fields_present(self):
        renderer = JsonRenderer()
        data = json.loads(renderer.render(_make_changelog()))
        commits = list(data["entries"][0]["groups"].values())[0]
        assert len(commits) > 0
        first = commits[0]
        assert "sha" in first and "message" in first


class TestTwitterRenderer:
    def test_render_without_llm(self):
        renderer = TwitterRenderer(model="", project_name="MyApp")
        entry = _make_entry()
        # Should not raise; uses fallback path
        output = renderer.render(entry)
        assert len(output) <= 280
        assert len(output) > 0

    def test_includes_version(self):
        renderer = TwitterRenderer(model="", project_name="MyApp")
        output = renderer.render(_make_entry())
        assert "v1.2.0" in output or "MyApp" in output
