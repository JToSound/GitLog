# Copilot instructions for LogForge

## Build, test, and lint commands

CI uses `uv`; prefer these commands:

```bash
uv sync --extra dev
uv run ruff check src/ tests/
uv run mypy src/gitlog
uv run pytest
uv run pytest --cov=src/gitlog --cov-report=xml --cov-report=term-missing
uv run pytest tests/test_git.py::TestGitLogParser::test_get_commits_returns_list -v
uv build
```

If `uv` is unavailable locally, install editable with dev extras and run tools via `python -m ...`:

```bash
python -m pip install -e .[dev]
```

## High-level architecture

- **CLI orchestration**: `src/gitlog/cli.py` is the Typer entrypoint. Commands load config, fetch commits, generate a `Changelog`, then dispatch to a renderer (`markdown`, `json`, `html`, `twitter`).
- **Config loading + precedence**: `src/gitlog/config.py` loads `.gitlog.toml` (`[gitlog]`, `[gitlog.prompts]`, `[gitlog.github]`) and applies `GITLOG_` env vars via `BaseSettings`.
- **Core generation pipeline**:
  1. `GitLogParser` (`src/gitlog/core/git.py`) reads commits/tags (GitPython-first, subprocess fallback) and parses conventional commit metadata plus PR/issue/co-author references.
  2. `CommitClassifier` (`src/gitlog/core/classifier.py`) runs a rule-based pass first, then batched LLM fallback for unmatched commits.
  3. `ChangelogGenerator` (`src/gitlog/core/generator.py`) applies exclude regexes, near-duplicate removal, grouping by `CommitType`, and per-group truncation.
  4. Renderers in `src/gitlog/renderers/` format output; Markdown/HTML optionally add GitHub commit links when `github.repo` is set.
- **Shared data model contract**: `src/gitlog/core/models.py` defines canonical models (`Commit`, `ChangelogEntry`, `Changelog`) used across parser/classifier/generator/renderers.

## Key codebase conventions

- **Compatibility in models is intentional**: tests and fixtures rely on legacy input shapes (`author` as string, `date` alias for `timestamp`). Preserve normalization behavior in `Commit` and legacy list synchronization in `ChangelogEntry`.
- **Parser testability pattern**: tests patch `gitlog.core.git.Repo`; keep the module-level `Repo` symbol and GitPython-first path intact when changing parser internals.
- **Classifier behavior is rule-first and batch-oriented**: never introduce per-commit LLM loops. Keep non-fatal fallback behavior where unresolved/failed classifications end up as `CommitType.MISC`.
- **Category ordering is shared behavior**: changelog section order is defined by `_CATEGORY_ORDER`/`CommitType` and consumed by generation + rendering paths.
- **Config options are tightly validated**: adding a new language/format requires synchronized changes in `GitlogConfig` validators and CLI enums.
- **Naming gotcha from README**: package/project name is `logforge-gitlog`, but importable module and CLI command are `gitlog`.
