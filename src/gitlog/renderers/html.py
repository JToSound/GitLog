"""HTML renderer using Jinja2 templates."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from gitlog.core.models import Changelog, Commit, CommitType

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_CATEGORY_COLORS: dict[CommitType, str] = {
    CommitType.BREAKING: "#f97316",
    CommitType.FEAT: "#3b82f6",
    CommitType.FIX: "#ef4444",
    CommitType.PERF: "#8b5cf6",
    CommitType.REFACTOR: "#06b6d4",
    CommitType.DOCS: "#10b981",
    CommitType.CHORE: "#6b7280",
    CommitType.MISC: "#9ca3af",
}

_I18N_LABELS: dict[str, dict[str, str]] = {
    "en": {"title": "📋 Changelog", "toggle": "Toggle Dark Mode", "scope": "Scope"},
    "zh-TW": {"title": "📋 變更日誌", "toggle": "切換深色模式", "scope": "範圍"},
    "zh-CN": {"title": "📋 变更日志", "toggle": "切换深色模式", "scope": "范围"},
    "ja": {"title": "📋 変更履歴", "toggle": "ダークモード切替", "scope": "スコープ"},
}


class HtmlRenderer:
    """Renders a Changelog to a self-contained HTML file."""

    def __init__(
        self,
        github_repo: str | None = None,
        language: str = "en",
        group_by_scope: bool = False,
    ) -> None:
        self._github_repo = github_repo
        self._language = language if language in _I18N_LABELS else "en"
        self._group_by_scope = group_by_scope
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )

    def render(self, changelog: Changelog) -> str:
        """Render a Changelog to HTML.

        Args:
            changelog: The Changelog to render.

        Returns:
            A self-contained HTML string.
        """
        template = self._env.get_template("report.html.j2")
        entries = [self._to_view_entry(entry) for entry in changelog.entries]
        return template.render(
            entries=entries,
            github_repo=self._github_repo,
            category_colors=_CATEGORY_COLORS,
            labels=_I18N_LABELS[self._language],
            language=self._language,
            group_by_scope=self._group_by_scope,
        )

    def _to_view_entry(self, entry: Any) -> dict[str, Any]:
        categories: list[dict[str, Any]] = []
        for commit_type, commits in entry.groups.items():
            if not commits:
                continue
            categories.append(
                {
                    "type": commit_type,
                    "type_label": commit_type.value,
                    "scopes": self._group_scopes(commits),
                }
            )
        return {
            "version": entry.version,
            "date": entry.date,
            "categories": categories,
        }

    def _group_scopes(self, commits: list[Commit]) -> list[dict[str, Any]]:
        if not self._group_by_scope:
            return [{"name": "", "commits": commits}]
        grouped: dict[str, list[Commit]] = defaultdict(list)
        for commit in commits:
            grouped[(commit.scope or "").strip()].append(commit)
        ordered_scopes = sorted(grouped.keys(), key=lambda key: (key == "", key))
        return [{"name": scope, "commits": grouped[scope]} for scope in ordered_scopes]
