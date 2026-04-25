# LogForge — gitlog

**LogForge — AI驱动的变更日志和发布说明生成器**

[![CI](https://github.com/JToSound/LogForge/actions/workflows/ci.yml/badge.svg)](https://github.com/JToSound/LogForge/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/JToSound/LogForge/branch/main/graph/badge.svg)](https://codecov.io/gh/JToSound/LogForge)
[![GitHub Releases](https://img.shields.io/github/v/release/JToSound/LogForge)](https://github.com/JToSound/LogForge/releases)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一条命令。从git历史到人类可读的结构化CHANGELOG。
支持**多种语言**、**多种输出格式**，以及**任何LLM**。

---

## 快速开始

### 1. 安装

```bash
# 推荐：uv（最快）
uv tool install gitlog

# 或者 pip
pip install gitlog

# 或者直接从GitHub安装
pip install git+https://github.com/JToSound/LogForge.git
```

**要求：** Python 3.11+ 和 Git。

### 2. 配置API密钥

```bash
# 选项A：环境变量（推荐用于CI）
export OPENAI_API_KEY="***"

# 选项B：在仓库根目录创建.env文件
echo "OPENAI_API_KEY=***" > .env

# 选项C：使用本地模型（不需要密钥）
gitlog generate --model ollama/llama3
```

### 3. 生成您的第一个变更日志

```bash
cd your-repo
gitlog generate
```

就是这样。您的 `CHANGELOG.md` 就准备好了。🎉

> **gitlog新手？** 运行 `gitlog init` 启动交互式设置向导，为您的项目创建定制的 `.gitlog.toml` 文件。

---

## 5秒演示

下面是一个非常短的演示，展示了 `gitlog generate` 如何在小型仓库中不到5秒内生成变更日志。

![快速演示](docs/demo.svg)

---

## 功能特性

- 🤖 **双层分类** — 规则引擎（零API成本） + LLM批量回退
- 🌍 **多语言输出** — 英语、繁体中文、简体中文、日语
- 📄 **多种格式** — Markdown（Keep-a-Changelog）、JSON、HTML、Twitter草稿
- 🔗 **GitHub集成** — 自动生成PR/issue/commit链接
- ⚡ **批量LLM调用** — 永远不会在循环中调用LLM；尊重token预算
- 🔄 **回退链** — LLM失败 → 规则引擎，绝不会中断流程
- 🧩 **CI/CD就绪** — 开箱即用的GitHub Actions工作流
- 🏠 **本地推理** — Ollama支持完全私密的生成

---

## 安装

```bash
# 推荐：使用uv
uv tool install gitlog

# 或者pip
pip install gitlog
```

**要求：** Python 3.11+, Git

---

## 用法

```bash
# 生成完整的CHANGELOG
gitlog generate

# 从特定版本开始
gitlog generate --since v1.2.0

# HTML报告
gitlog generate --format html

# 繁体中文输出
gitlog generate --lang zh-TW

# 使用本地Ollama模型（不需要API密钥）
gitlog generate --model ollama/llama3

# 在终端预览而不写入文件
gitlog generate --dry-run

# 比较两个版本
gitlog diff v1.0.0 v1.1.0

# 生成Twitter/X公告
gitlog tweet

# ASCII提交统计
gitlog stats

# 交互式设置
gitlog init
```

---

## 配置

在您的仓库根目录创建 `.gitlog.toml`（或者运行 `gitlog init`）：

```toml
[gitlog]
llm_provider = "openai"
model = "gpt-4o-mini"
language = "en"
format = "markdown"
output_file = "CHANGELOG.md"
project_description = "一个开发者工具用于..."
exclude_patterns = ["^chore\\(deps\\)", "^Merge branch"]
group_by_scope = true
max_commits_per_group = 20

[gitlog.github]
repo = "owner/repo"
```

### 完整配置参考

| 参数 | 默认值 | 描述 |
|---|---|---|
| `llm_provider` | `openai` | LLM提供商：`openai`、`anthropic`、`ollama` |
| `model` | `gpt-4o-mini` | 模型标识符 |
| `language` | `en` | 输出语言：`en`、`zh-TW`、`zh-CN`、`ja` |
| `format` | `markdown` | 输出格式：`markdown`、`json`、`html`、`twitter` |
| `output_file` | `CHANGELOG.md` | 输出文件路径 |
| `project_description` | `""` | 项目上下文注入到LLM提示中 |
| `exclude_patterns` | 见默认值 | 要跳过的提交消息的正则表达式列表 |
| `group_by_scope` | `true` | 按约定提交范围分组提交 |
| `max_commits_per_group` | `20` | 每个版本每个类别的最大提交数 |
| `github.repo` | `""` | `owner/repo` 用于生成可点击链接 |

---

## GitHub Actions集成

添加到您的发布工作流：

```yaml
- name: Generate Changelog
  uses: JToSound/LogForge/.github/workflows/release.yml@main
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

或者使用包含的 `release.yml`，它会自动：
1. 在标签推送时构建并发布到PyPI
2. 使用gitlog本身生成变更日志
3. 创建带有生成的说明的GitHub Release

---

## 支持的LLM提供商

| 提供商 | 模型示例 | 环境变量 |
|---|---|---|
| OpenAI | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude-3-5-haiku-20241022` | `ANTHROPIC_API_KEY` |
| Ollama (本地) | `ollama/llama3` | *(不需要)* |
| Gemini | `gemini/gemini-1.5-flash` | `GEMINI_API_KEY` |

---

## 许可证

MIT © gitlog贡献者