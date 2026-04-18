"""Keep-a-Changelog Markdown renderer."""
from __future__ import annotations

from collections import defaultdict

from gitlog.core.models import _CATEGORY_ORDER, Changelog, ChangelogEntry, Commit, CommitType

_SECTION_TITLES: dict[str, dict[CommitType, str]] = {
    "en": {
        CommitType.BREAKING: "⚠️ Breaking Changes",
        CommitType.FEAT: "✨ Features",
        CommitType.FIX: "🐛 Bug Fixes",
        CommitType.PERF: "⚡ Performance",
        CommitType.REFACTOR: "♻️ Refactoring",
        CommitType.DOCS: "📝 Documentation",
        CommitType.CHORE: "🔧 Chores",
        CommitType.MISC: "📦 Miscellaneous",
    },
    "zh-TW": {
        CommitType.BREAKING: "⚠️ 重大破壞性變更",
        CommitType.FEAT: "✨ 新功能",
        CommitType.FIX: "🐛 錯誤修復",
        CommitType.PERF: "⚡ 效能改善",
        CommitType.REFACTOR: "♻️ 重構",
        CommitType.DOCS: "📝 文件更新",
        CommitType.CHORE: "🔧 維護工作",
        CommitType.MISC: "📦 其他變更",
    },
    "zh-CN": {
        CommitType.BREAKING: "⚠️ 重大破坏性变更",
        CommitType.FEAT: "✨ 新功能",
        CommitType.FIX: "🐛 错误修复",
        CommitType.PERF: "⚡ 性能优化",
        CommitType.REFACTOR: "♻️ 重构",
        CommitType.DOCS: "📝 文档更新",
        CommitType.CHORE: "🔧 维护事项",
        CommitType.MISC: "📦 其他变更",
    },
    "ja": {
        CommitType.BREAKING: "⚠️ 破壊的変更",
        CommitType.FEAT: "✨ 新機能",
        CommitType.FIX: "🐛 バグ修正",
        CommitType.PERF: "⚡ パフォーマンス改善",
        CommitType.REFACTOR: "♻️ リファクタリング",
        CommitType.DOCS: "📝 ドキュメント",
        CommitType.CHORE: "🔧 メンテナンス",
        CommitType.MISC: "📦 その他",
    },
}

_I18N_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "title": "# Changelog\n",
        "intro_1": "All notable changes to this project will be documented in this file.\n",
        "intro_2": "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),",
        "intro_3": "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n",
        "scope": "Scope",
    },
    "zh-TW": {
        "title": "# 變更日誌\n",
        "intro_1": "本專案所有重要變更都會記錄於此。\n",
        "intro_2": "格式參考 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，",
        "intro_3": "並遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。\n",
        "scope": "範圍",
    },
    "zh-CN": {
        "title": "# 变更日志\n",
        "intro_1": "本项目所有重要变更都会记录在此。\n",
        "intro_2": "格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，",
        "intro_3": "并遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。\n",
        "scope": "范围",
    },
    "ja": {
        "title": "# 変更履歴\n",
        "intro_1": "このプロジェクトの重要な変更はすべてこのファイルに記録されます。\n",
        "intro_2": "形式は [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) に準拠し、",
        "intro_3": (
            "本プロジェクトは "
            "[Semantic Versioning](https://semver.org/spec/v2.0.0.html) "
            "に従います。\n"
        ),
        "scope": "スコープ",
    },
}


class MarkdownRenderer:
    """Renders a Changelog to Keep-a-Changelog Markdown format."""

    def __init__(
        self,
        github_repo: str | None = None,
        language: str = "en",
        group_by_scope: bool = False,
    ) -> None:
        self._github_repo = github_repo
        self._language = language if language in _I18N_TEXT else "en"
        self._group_by_scope = group_by_scope

    def render(self, changelog: Changelog) -> str:
        """Render a full Changelog to a Markdown string.

        Args:
            changelog: The Changelog to render.

        Returns:
            A Markdown-formatted string.
        """
        text = _I18N_TEXT[self._language]
        lines: list[str] = [
            text["title"],
            text["intro_1"],
            text["intro_2"],
            text["intro_3"],
        ]
        for entry in changelog.entries:
            lines.append(self._render_entry(entry))
        return "\n".join(lines)

    def render_entry(self, entry: ChangelogEntry) -> str:
        """Render a single ChangelogEntry section.

        Args:
            entry: The entry to render.

        Returns:
            Markdown string for one version block.
        """
        return self._render_entry(entry)

    def _render_entry(self, entry: ChangelogEntry) -> str:
        date_str = f" - {entry.date}" if entry.date else ""
        lines: list[str] = [f"## [{entry.version}]{date_str}\n"]

        section_titles = _SECTION_TITLES[self._language]
        for ct in _CATEGORY_ORDER:
            commits = entry.groups.get(ct, [])
            if not commits:
                continue
            lines.append(f"### {section_titles.get(ct, ct.value)}\n")
            for scope, scoped_commits in self._group_scopes(commits):
                if self._group_by_scope and scope:
                    scope_title = _I18N_TEXT[self._language]["scope"]
                    lines.append(f"#### {scope_title}: `{scope}`\n")
                for commit in scoped_commits:
                    sha_link = self._sha_link(commit.sha)
                    lines.append(f"- {commit.message} {sha_link}".rstrip())
            lines.append("")

        return "\n".join(lines)

    def _group_scopes(self, commits: list[Commit]) -> list[tuple[str, list[Commit]]]:
        if not self._group_by_scope:
            return [("", commits)]
        grouped: dict[str, list[Commit]] = defaultdict(list)
        for commit in commits:
            key = (commit.scope or "").strip()
            grouped[key].append(commit)
        ordered_scopes = sorted(grouped.keys(), key=lambda k: (k == "", k))
        return [(scope, grouped[scope]) for scope in ordered_scopes]

    def _sha_link(self, sha: str) -> str:
        if self._github_repo:
            url = f"https://github.com/{self._github_repo}/commit/{sha}"
            return f"([`{sha[:7]}`]({url}))"
        return f"(`{sha[:7]}`)"
