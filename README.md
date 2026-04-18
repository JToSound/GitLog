<div align="center">

# LogForge — gitlog

**LogForge — AI-Powered Changelog & Release Notes Generator**

[![CI](https://github.com/JToSound/LogForge/actions/workflows/ci.yml/badge.svg)](https://github.com/JToSound/LogForge/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/JToSound/LogForge/branch/main/graph/badge.svg)](https://codecov.io/gh/JToSound/LogForge)
[![GitHub Releases](https://img.shields.io/github/v/release/JToSound/LogForge)](https://github.com/JToSound/LogForge/releases)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

One command. From git history to a human-readable, structured CHANGELOG.  
Supports **multiple languages**, **multiple output formats**, and **any LLM**.

## Getting Started with LogForge

LogForge is an AI-powered changelog and release notes generator. It's designed to be easy to use and integrate into your development workflow. Here's a step-by-step guide to get you started:

1. **Install LogForge**: You can install LogForge directly from GitHub using pip: `pip install git+https://github.com/JToSound/LogForge.git`
2. **Set up your repository**: Navigate to your repository and set the `OPENAI_API_KEY` environment variable: `export OPENAI_API_KEY=sk-...`
3. **Generate your changelog**: Run the command `gitlog generate` to generate your changelog.

That's it! Your `CHANGELOG.md` is ready. 

## Quick Start

```bash
# Install directly from GitHub (recommended until published to PyPI)
pip install git+https://github.com/JToSound/LogForge.git
cd your-repo
export OPENAI_API_KEY=sk-...
gitlog generate
```

## 5s Demo

Below is a very short demo that shows `gitlog generate` producing a changelog in under 5 seconds on small repos.

![Quick demo](docs/demo.svg)

## Features

- 🤖 **Two-layer classification** — rule engine (zero API cost) + LLM batch fallback
- 🌍 **Multilingual output** — English, Traditional Chinese, Simplified Chinese, Japanese
- 📄 **Multiple formats** — Markdown (Keep-a-Changelog), JSON, HTML, Twitter drafts
- 🔗 **GitHub integration** — auto-generates PR/issue/commit links
- ⚡ **Batch LLM calls** — never call the LLM in a loop; respects token budgets
- 🔄 **Fallback chain** — LLM failure → rule engine, never interrupts the flow
- 🧩 **CI/CD ready** — GitHub Actions workflow included out of the box
- 🏠 **Local inference** — Ollama support for fully private generation

## Installation

```bash
# Recommended: with uv
uv tool install gitlog

# Or pip
pip install gitlog
```

**Requirements:** Python 3.11+, Git

## Usage

```bash
# Generate full CHANGELOG
gitlog generate

# From a specific version
gitlog generate --since v1.2.0

# HTML report
gitlog generate --format html

# Traditional Chinese output
gitlog generate --lang zh-TW

# Use a local Ollama model (no API key needed)
gitlog generate --model ollama/llama3

# Preview in terminal without writing a file
gitlog generate --dry-run

# Compare two versions
gitlog diff v1.0.0 v1.1.0

# Generate Twitter/X announcement
gitlog tweet

# ASCII commit statistics
gitlog stats

# Interactive setup
gitlog init
```

## Configuration

Create a `.gitlog.toml` in your repo root (or run `gitlog init`):

```toml
[gitlog]
llm_provider = "openai"
model = "gpt-4o-mini"
language = "en"
format = "markdown"
output_file = "CHANGELOG.md"
project_description = "A developer tool for..."
exclude_patterns = ["^chore\\(deps\\)", "^Merge branch"]
group_by_scope = true
max_commits_per_group = 20

[gitlog.github]
repo = "owner/repo"
```

### Full Configuration Reference

| Parameter | Default | Description |
|---|---|---|
| `llm_provider` | `openai` | LLM provider: `openai`, `anthropic`, `ollama` |
| `model` | `gpt-4o-mini` | Model identifier |
| `language` | `en` | Output language: `en`, `zh-TW`, `zh-CN`, `ja` |
| `format` | `markdown` | Output format: `markdown`, `json`, `html`, `twitter` |
| `output_file` | `CHANGELOG.md` | Output file path |
| `project_description` | `""` | Project context injected into LLM prompts |
| `exclude_patterns` | see default | Regex list of commit messages to skip |
| `group_by_scope` | `true` | Group commits by conventional commit scope |
| `max_commits_per_group` | `20` | Max commits shown per category per version |
| `github.repo` | `""` | `owner/repo` for generating clickable links |

## GitHub Actions Integration

Add to your release workflow:

```yaml
- name: Generate Changelog
  uses: JToSound/LogForge/.github/workflows/release.yml@main
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

Or use the included `release.yml` which automatically:
1. Builds and publishes to PyPI on tag push
2. Generates the changelog using gitlog itself
3. Creates a GitHub Release with the generated notes

## Supported LLM Providers

| Provider | Model Example | Env Var |
|---|---|---|
| OpenAI | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude-3-5-haiku-20241022` | `ANTHROPIC_API_KEY` |
| Ollama (local) | `ollama/llama3` | *(none required)* |
| Gemini | `gemini/gemini-1.5-flash` | `GEMINI_API_KEY` |

## License

MIT © gitlog contributors