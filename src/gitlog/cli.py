"""Typer CLI entry point for gitlog."""
from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from gitlog import __version__
from gitlog.config import GitlogConfig, load_settings
from gitlog.core.classifier import CommitClassifier, RuleBasedClassifier
from gitlog.core.generator import ChangelogGenerator
from gitlog.core.git import GitLogParser
from gitlog.core.models import Changelog, Commit, CommitType, Tag
from gitlog.exceptions import GitlogError

app = typer.Typer(
    name="gitlog",
    help="AI-Powered Changelog & Release Notes Generator.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()
_SEMVER_TAG_PATTERN = re.compile(r"^(?P<prefix>v?)(?P<maj>\d+)\.(?P<min>\d+)\.(?P<pat>\d+)")


class OutputFormat(str, Enum):
    """Supported output formats."""

    markdown = "markdown"
    json = "json"
    html = "html"
    twitter = "twitter"


class Language(str, Enum):
    """Supported output languages."""

    en = "en"
    zh_tw = "zh-TW"
    zh_cn = "zh-CN"
    ja = "ja"


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        rprint(f"[bold cyan]gitlog[/] version [bold]{__version__}[/]")
        raise typer.Exit()


def _render_changelog(settings: GitlogConfig, changelog: Changelog) -> str:
    """Render a changelog using the selected output format."""
    if settings.format == "markdown":
        from gitlog.renderers.markdown import MarkdownRenderer

        return MarkdownRenderer(
            github_repo=settings.github.repo or None,
            language=settings.language,
            group_by_scope=settings.group_by_scope,
        ).render(changelog)
    if settings.format == "json":
        from gitlog.renderers.json import JsonRenderer

        return JsonRenderer().render(changelog)
    if settings.format == "html":
        from gitlog.renderers.html import HtmlRenderer

        return HtmlRenderer(
            github_repo=settings.github.repo or None,
            language=settings.language,
            group_by_scope=settings.group_by_scope,
        ).render(changelog)

    # Fallback to markdown for unknown formats.
    from gitlog.renderers.markdown import MarkdownRenderer

    return MarkdownRenderer(
        github_repo=settings.github.repo or None,
        language=settings.language,
        group_by_scope=settings.group_by_scope,
    ).render(changelog)


def _parse_latest_semver_tag(tags: list[Tag]) -> tuple[Tag | None, str, int, int, int]:
    for tag in tags:
        match = _SEMVER_TAG_PATTERN.match(tag.name)
        if match:
            return (
                tag,
                match.group("prefix"),
                int(match.group("maj")),
                int(match.group("min")),
                int(match.group("pat")),
            )
    return None, "v", 0, 0, 0


def _determine_bump(commits: list[Commit]) -> str:
    types = {commit.commit_type for commit in commits}
    if CommitType.BREAKING in types:
        return "major"
    if CommitType.FEAT in types:
        return "minor"
    if commits:
        return "patch"
    return "none"


def _next_version(prefix: str, major: int, minor: int, patch: int, bump: str) -> str:
    if bump == "major":
        return f"{prefix}{major + 1}.0.0"
    if bump == "minor":
        return f"{prefix}{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{prefix}{major}.{minor}.{patch + 1}"
    return f"{prefix}{major}.{minor}.{patch}"


def _apply_prerelease(version: str, prerelease_type: str) -> str:
    """Attach prerelease suffix to a semver tag string."""
    return f"{version}-{prerelease_type}.1"


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """[bold cyan]gitlog[/] — AI-Powered Changelog & Release Notes Generator."""


@app.command()
def generate(
    since: Annotated[
        str | None,
        typer.Option(help="Tag, date, or commit hash to start from."),
    ] = None,
    until: Annotated[
        str | None,
        typer.Option(help="Tag, date, or commit hash to stop at."),
    ] = None,
    format: Annotated[
        OutputFormat,
        typer.Option(help="Output format."),
    ] = OutputFormat.markdown,
    lang: Annotated[
        Language,
        typer.Option(help="Output language."),
    ] = Language.en,
    model: Annotated[
        str | None,
        typer.Option(help="LLM model string, e.g. ollama/llama3."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path."),
    ] = None,
    paths: Annotated[
        list[str] | None,
        typer.Option("--path", "-p", help="Only include commits touching this path (repeatable)."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview output without writing."),
    ] = False,
    repo_path: Annotated[
        Path,
        typer.Option("--repo", help="Path to git repository."),
    ] = Path("."),
) -> None:
    """Generate a changelog from git history."""
    try:
        settings = load_settings()
        if model:
            settings.model = model
        settings.language = lang.value
        settings.format = format.value

        out_path = output or Path(settings.output_file)
        selected_paths = paths if paths else (settings.paths or None)
        max_count = settings.commit_search_depth if settings.commit_search_depth > 0 else None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Fetching commits...", total=None)
            parser = GitLogParser(repo_path=repo_path)
            commits = parser.get_commits(
                since=since, until=until, paths=selected_paths, max_count=max_count
            )
            progress.update(task, description=f"[green]✓[/] Fetched {len(commits)} commits")

            progress.add_task("Classifying & generating...", total=None)
            generator = ChangelogGenerator(config=settings)
            changelog = generator.generate(commits=commits)

        result = _render_changelog(settings, changelog)

        if dry_run:
            console.print(
                Panel(result, title="[bold]Changelog Preview[/]", border_style="cyan")
            )
            return

        out_path.write_text(result, encoding="utf-8")
        console.print(
            Panel(
                f"[green]✓[/] Changelog written to [bold]{out_path}[/]\n"
                f"  Processed [bold]{len(commits)}[/] commits",
                title="gitlog",
                border_style="green",
            )
        )
    except GitlogError as exc:
        error_text = (
            f"[red bold]Error:[/] {exc}\n\n[yellow]Hint:[/] {exc.hint}"
            if exc.hint
            else f"[red bold]Error:[/] {exc}"
        )
        console.print(Panel(error_text, title="gitlog error", border_style="red"))
        raise typer.Exit(1) from exc


@app.command()
def preview(
    repo_path: Annotated[
        Path,
        typer.Option("--repo", help="Path to git repository."),
    ] = Path("."),
    paths: Annotated[
        list[str] | None,
        typer.Option("--path", "-p", help="Only include commits touching this path (repeatable)."),
    ] = None,
) -> None:
    """Rich terminal preview of the latest changelog."""
    try:
        settings = load_settings()
        settings.language = Language.en.value
        settings.format = OutputFormat.markdown.value

        selected_paths = paths if paths else (settings.paths or None)
        max_count = settings.commit_search_depth if settings.commit_search_depth > 0 else None
        parser = GitLogParser(repo_path=repo_path)
        commits = parser.get_commits(paths=selected_paths, max_count=max_count)
        generator = ChangelogGenerator(config=settings)
        changelog = generator.generate(commits=commits)
        rendered = _render_changelog(settings, changelog)
        console.print(Panel(rendered, title="[bold]Changelog Preview[/]", border_style="cyan"))
    except GitlogError as exc:
        console.print(Panel(f"[red]{exc}[/]", border_style="red"))
        raise typer.Exit(1) from exc


@app.command()
def diff(
    from_tag: Annotated[str, typer.Argument(help="Start tag/commit.")],
    to_tag: Annotated[str, typer.Argument(help="End tag/commit.")],
    repo_path: Annotated[Path, typer.Option("--repo")] = Path("."),
    paths: Annotated[
        list[str] | None,
        typer.Option("--path", "-p", help="Only include commits touching this path (repeatable)."),
    ] = None,
) -> None:
    """Show changelog diff between two versions."""
    try:
        settings = load_settings()
        selected_paths = paths if paths else (settings.paths or None)
        max_count = settings.commit_search_depth if settings.commit_search_depth > 0 else None
        parser = GitLogParser(repo_path=repo_path)
        commits = parser.get_commits(
            since=from_tag, until=to_tag, paths=selected_paths, max_count=max_count
        )
        generator = ChangelogGenerator(config=settings)
        changelog = generator.generate(commits=commits)

        from gitlog.renderers.markdown import MarkdownRenderer

        rendered = MarkdownRenderer(github_repo=settings.github.repo or None).render(changelog)
        panel = Panel(rendered, title=f"[bold]{from_tag} → {to_tag}[/]", border_style="blue")
        console.print(panel)
    except GitlogError as exc:
        console.print(Panel(f"[red]{exc}[/]", border_style="red"))
        raise typer.Exit(1) from exc


@app.command()
def tweet(
    since: Annotated[
        str | None,
        typer.Option(help="Tag to generate tweet from."),
    ] = None,
    repo_path: Annotated[Path, typer.Option("--repo")] = Path("."),
    paths: Annotated[
        list[str] | None,
        typer.Option("--path", "-p", help="Only include commits touching this path (repeatable)."),
    ] = None,
) -> None:
    """Generate a Twitter/X release announcement."""
    try:
        settings = load_settings()
        settings.format = "twitter"
        selected_paths = paths if paths else (settings.paths or None)
        max_count = settings.commit_search_depth if settings.commit_search_depth > 0 else None
        parser = GitLogParser(repo_path=repo_path)
        commits = parser.get_commits(since=since, paths=selected_paths, max_count=max_count)
        generator = ChangelogGenerator(config=settings)
        changelog = generator.generate(commits=commits)

        # Choose the most relevant entry (Unreleased or latest).
        entry = changelog.entries[0] if changelog.entries else generator.generate_unreleased()
        from gitlog.renderers.twitter import TwitterRenderer

        renderer = TwitterRenderer(model=settings.model, project_name=settings.project_name)
        tweet_text = renderer.render(entry)
        console.print(Panel(tweet_text, title="🐦 Tweet Draft", border_style="blue"))
    except GitlogError as exc:
        console.print(Panel(f"[red]{exc}[/]", border_style="red"))
        raise typer.Exit(1) from exc


@app.command()
def stats(
    since: Annotated[
        str | None,
        typer.Option(help="Start from tag/date."),
    ] = None,
    repo_path: Annotated[Path, typer.Option("--repo")] = Path("."),
    paths: Annotated[
        list[str] | None,
        typer.Option("--path", "-p", help="Only include commits touching this path (repeatable)."),
    ] = None,
) -> None:
    """Display commit type statistics as an ASCII bar chart."""
    try:
        settings = load_settings()
        selected_paths = paths if paths else (settings.paths or None)
        max_count = settings.commit_search_depth if settings.commit_search_depth > 0 else None
        parser = GitLogParser(repo_path=repo_path)
        commits = parser.get_commits(since=since, paths=selected_paths, max_count=max_count)

        classifier = RuleBasedClassifier()
        counts: dict[str, int] = {}
        for commit in commits:
            commit_type = classifier.classify(commit) or CommitType.MISC
            label = commit_type.value
            counts[label] = counts.get(label, 0) + 1

        total = max(sum(counts.values()), 1)
        table = Table(title="Commit Statistics", show_header=True)
        table.add_column("Type", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Distribution")

        colors = {
            "feat": "blue",
            "fix": "red",
            "perf": "yellow",
            "refactor": "cyan",
            "docs": "green",
            "chore": "dim",
            "breaking": "bold red",
            "misc": "white",
        }
        for label, count in sorted(counts.items(), key=lambda x: -x[1]):
            bar_len = int((count / total) * 40)
            color = colors.get(label, "white")
            bar = "█" * bar_len
            table.add_row(label, str(count), f"[{color}]{bar}[/]")

        console.print(table)
    except GitlogError as exc:
        console.print(Panel(f"[red]{exc}[/]", border_style="red"))
        raise typer.Exit(1) from exc


@app.command("next-version")
def next_version(
    repo_path: Annotated[Path, typer.Option("--repo", help="Path to git repository.")] = Path("."),
    paths: Annotated[
        list[str] | None,
        typer.Option("--path", "-p", help="Only include commits touching this path (repeatable)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print machine-readable JSON output."),
    ] = False,
    prerelease: Annotated[
        str | None,
        typer.Option(
            "--prerelease",
            help="Optional prerelease channel (alpha/beta/rc).",
        ),
    ] = None,
    hotfix: Annotated[
        bool,
        typer.Option("--hotfix", help="Force patch bump for emergency hotfix release."),
    ] = False,
) -> None:
    """Predict the next semantic version from commits since the latest tag."""
    try:
        settings = load_settings()
        selected_paths = paths if paths else (settings.paths or None)
        max_count = settings.commit_search_depth if settings.commit_search_depth > 0 else None

        parser = GitLogParser(repo_path=repo_path)
        tags = parser.get_tags()
        latest_tag, prefix, major, minor, patch = _parse_latest_semver_tag(tags)
        since_tag = latest_tag.name if latest_tag else None

        commits = parser.get_commits(since=since_tag, paths=selected_paths, max_count=max_count)
        classified = CommitClassifier(settings).classify_all(commits)
        bump = _determine_bump(classified)
        if hotfix and bump != "none":
            bump = "patch"
        current_version = f"{prefix}{major}.{minor}.{patch}"
        next_ver = _next_version(prefix, major, minor, patch, bump)
        if prerelease:
            normalized = prerelease.strip().lower()
            if normalized not in {"alpha", "beta", "rc"}:
                raise typer.BadParameter("prerelease must be one of: alpha, beta, rc")
            next_ver = _apply_prerelease(next_ver, normalized)

        payload = {
            "current_version": current_version,
            "next_version": next_ver,
            "bump": bump,
            "since_tag": since_tag,
            "commits_analyzed": len(classified),
            "prerelease": prerelease.lower() if prerelease else None,
            "hotfix": hotfix,
        }
        if json_output:
            console.print(json.dumps(payload, ensure_ascii=False))
            return

        console.print(
            Panel(
                "\n".join(
                    [
                        f"Current: [bold]{current_version}[/]",
                        f"Next: [bold green]{next_ver}[/]",
                        f"Bump: [bold]{bump}[/]",
                        f"Commits analyzed: [bold]{len(classified)}[/]",
                    ]
                ),
                title="Next Version",
                border_style="green",
            )
        )
    except GitlogError as exc:
        console.print(Panel(f"[red]{exc}[/]", border_style="red"))
        raise typer.Exit(1) from exc


@app.command()
def init(
    repo_path: Annotated[Path, typer.Option("--repo")] = Path("."),
) -> None:
    """Interactively create a .gitlog.toml configuration file."""
    toml_path = repo_path / ".gitlog.toml"
    if toml_path.exists():
        overwrite = typer.confirm(f"{toml_path} already exists. Overwrite?", default=False)
        if not overwrite:
            raise typer.Exit()

    provider = typer.prompt("LLM provider (openai/anthropic/ollama/gemini)", default="openai")
    model = typer.prompt("Model", default="gpt-4o-mini")
    language = typer.prompt("Output language (en/zh-TW/zh-CN/ja)", default="en")
    description = typer.prompt("Short project description", default="")
    github_repo = typer.prompt("GitHub repo (owner/repo, leave blank to skip)", default="")

    config_lines = [
        "[gitlog]",
        f'llm_provider = "{provider}"',
        f'model = "{model}"',
        f'language = "{language}"',
        'format = "markdown"',
        'output_file = "CHANGELOG.md"',
    ]
    if description:
        config_lines.append(f'project_description = "{description}"')
    config_lines += [
        'exclude_patterns = ["^chore\\\\(deps\\\\)", "^Merge branch"]',
        "group_by_scope = true",
        "max_commits_per_group = 20",
        "paths = []",
        "commit_search_depth = 0",
        "llm_batch_size = 40",
        "",
        "[gitlog.prompts]",
        'classify_system = ""',
        'summarize_system = ""',
    ]
    if github_repo:
        config_lines += ["", "[gitlog.github]", f'repo = "{github_repo}"']

    toml_path.write_text("\n".join(config_lines) + "\n", encoding="utf-8")
    success_text = (
        f"[green]✓[/] Created [bold]{toml_path}[/]\n\n"
        "Run [bold]gitlog generate[/] to create your first changelog."
    )
    console.print(Panel(success_text, title="gitlog init", border_style="green"))


if __name__ == "__main__":
    app()
