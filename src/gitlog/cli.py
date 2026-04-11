"""Typer CLI entry point for gitlog."""
from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint

from gitlog import __version__
from gitlog.config import GitlogSettings, load_settings
from gitlog.core.git import GitLogParser
from gitlog.core.generator import ChangelogGenerator
from gitlog.exceptions import GitlogError

app = typer.Typer(
    name="gitlog",
    help="AI-Powered Changelog & Release Notes Generator.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


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


@app.callback()
def main(
    version: Optional[bool] = typer.Option(  # noqa: UP007
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """[bold cyan]gitlog[/] \u2014 AI-Powered Changelog & Release Notes Generator."""


@app.command()
def generate(
    since: Optional[str] = typer.Option(None, help="Tag, date, or commit hash to start from."),  # noqa: UP007
    until: Optional[str] = typer.Option(None, help="Tag, date, or commit hash to stop at."),  # noqa: UP007
    format: OutputFormat = typer.Option(OutputFormat.markdown, help="Output format."),
    lang: Language = typer.Option(Language.en, help="Output language."),
    model: Optional[str] = typer.Option(None, help="LLM model string, e.g. ollama/llama3."),  # noqa: UP007
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path."),  # noqa: UP007
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview output without writing."),
    repo_path: Path = typer.Option(Path("."), "--repo", help="Path to git repository."),
) -> None:
    """Generate a changelog from git history."""
    try:
        settings = load_settings()
        if model:
            settings.model = model
        settings.language = lang.value
        settings.format = format.value

        out_path = output or Path(settings.output_file)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            t1 = progress.add_task("Fetching commits...", total=None)
            parser = GitLogParser(repo_path=repo_path)
            commits = parser.get_commits(since=since, until=until)
            progress.update(t1, description=f"[green]\u2713[/] Fetched {len(commits)} commits")

            progress.add_task("Classifying & generating...", total=None)
            generator = ChangelogGenerator(config=settings)
            changelog = generator.generate(commits=commits)

        # Render the Changelog using the requested format
        if settings.format == "markdown":
            from gitlog.renderers.markdown import MarkdownRenderer

            renderer = MarkdownRenderer(github_repo=settings.github.repo or None)
            result = renderer.render(changelog)
        elif settings.format == "json":
            from gitlog.renderers.json import JsonRenderer

            result = JsonRenderer().render(changelog)
        elif settings.format == "html":
            from gitlog.renderers.html import HtmlRenderer

            result = HtmlRenderer(github_repo=settings.github.repo or None).render(changelog)
        else:
            # fallback to markdown for unknown formats
            from gitlog.renderers.markdown import MarkdownRenderer

            result = MarkdownRenderer(github_repo=settings.github.repo or None).render(changelog)

        if dry_run:
            console.print(Panel(result, title="[bold]Changelog Preview[/]", border_style="cyan"))
        else:
            out_path.write_text(result, encoding="utf-8")
            console.print(
                Panel(
                    f"[green]\u2713[/] Changelog written to [bold]{out_path}[/]\n"
                    f"  Processed [bold]{len(commits)}[/] commits",
                    title="gitlog",
                    border_style="green",
                )
            )

    except GitlogError as exc:
        console.print(
            Panel(
                f"[red bold]Error:[/] {exc}\n\n[yellow]Hint:[/] {exc.hint}" if exc.hint else f"[red bold]Error:[/] {exc}",
                title="gitlog error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def preview(
    repo_path: Path = typer.Option(Path("."), "--repo", help="Path to git repository."),
) -> None:
    """Rich terminal preview of the latest changelog."""
    generate.callback(  # type: ignore[misc]
        since=None,
        until=None,
        format=OutputFormat.markdown,
        lang=Language.en,
        model=None,
        output=None,
        dry_run=True,
        repo_path=repo_path,
    )


@app.command()
def diff(
    from_tag: str = typer.Argument(..., help="Start tag/commit."),
    to_tag: str = typer.Argument(..., help="End tag/commit."),
    repo_path: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """Show changelog diff between two versions."""
    try:
        settings = load_settings()
        parser = GitLogParser(repo_path=repo_path)
        commits = parser.get_commits(since=from_tag, until=to_tag)
        generator = ChangelogGenerator(config=settings)
        changelog = generator.generate(commits=commits)

        from gitlog.renderers.markdown import MarkdownRenderer

        rendered = MarkdownRenderer(github_repo=settings.github.repo or None).render(changelog)
        console.print(Panel(rendered, title=f"[bold]{from_tag} \u2192 {to_tag}[/]", border_style="blue"))
    except GitlogError as exc:
        console.print(Panel(f"[red]{exc}[/]", border_style="red"))
        raise typer.Exit(1)


@app.command()
def tweet(
    since: Optional[str] = typer.Option(None, help="Tag to generate tweet from."),  # noqa: UP007
    repo_path: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """Generate a Twitter/X release announcement."""
    try:
        settings = load_settings()
        settings.format = "twitter"
        parser = GitLogParser(repo_path=repo_path)
        commits = parser.get_commits(since=since)
        generator = ChangelogGenerator(config=settings)
        changelog = generator.generate(commits=commits)

        # Choose the most-relevant entry (Unreleased or latest)
        entry = changelog.entries[0] if changelog.entries else generator.generate_unreleased()
        from gitlog.renderers.twitter import TwitterRenderer

        tweet = TwitterRenderer(model=settings.model, project_name=settings.project_name).render(entry)
        console.print(Panel(tweet, title="\U0001f426 Tweet Draft", border_style="blue"))
    except GitlogError as exc:
        console.print(Panel(f"[red]{exc}[/]", border_style="red"))
        raise typer.Exit(1)


@app.command()
def stats(
    since: Optional[str] = typer.Option(None, help="Start from tag/date."),  # noqa: UP007
    repo_path: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """Display commit type statistics as an ASCII bar chart."""
    try:
        from gitlog.core.classifier import RuleClassifier

        parser = GitLogParser(repo_path=repo_path)
        commits = parser.get_commits(since=since)
        classifier = RuleClassifier()
        counts: dict[str, int] = {}
        for commit in commits:
            label = classifier.classify(commit.message)
            counts[label] = counts.get(label, 0) + 1

        total = max(sum(counts.values()), 1)
        table = Table(title="Commit Statistics", show_header=True)
        table.add_column("Type", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Distribution")

        colors = {
            "feat": "blue", "fix": "red", "perf": "yellow",
            "refactor": "cyan", "docs": "green", "chore": "dim", "breaking": "bold red",
        }
        for label, count in sorted(counts.items(), key=lambda x: -x[1]):
            bar_len = int((count / total) * 40)
            color = colors.get(label, "white")
            table.add_row(label, str(count), f"[{color}]{'\u2588' * bar_len}[/]")

        console.print(table)
    except GitlogError as exc:
        console.print(Panel(f"[red]{exc}[/]", border_style="red"))
        raise typer.Exit(1)


@app.command()
def init(
    repo_path: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """Interactively create a .gitlog.toml configuration file."""
    toml_path = repo_path / ".gitlog.toml"
    if toml_path.exists():
        overwrite = typer.confirm(f"{toml_path} already exists. Overwrite?", default=False)
        if not overwrite:
            raise typer.Exit()

    provider = typer.prompt("LLM provider", default="openai")
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
        "",
        "[gitlog.prompts]",
        'classify_system = ""',
        'summarize_system = ""',
    ]
    if github_repo:
        config_lines += ["", "[gitlog.github]", f'repo = "{github_repo}"']

    toml_path.write_text("\n".join(config_lines) + "\n", encoding="utf-8")
    console.print(
        Panel(
            f"[green]\u2713[/] Created [bold]{toml_path}[/]\n\nRun [bold]gitlog generate[/] to create your first changelog.",
            title="gitlog init",
            border_style="green",
        )
    )


if __name__ == "__main__":
    app()
