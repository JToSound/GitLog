# Quick Demo (30s)

This file shows a short sequence to try the project locally. Run these from your shell.

POSIX / macOS / Linux:

```bash
# Clone and enter
git clone https://github.com/JToSound/LogForge.git demo-repo
cd demo-repo

# (recommended) install editable with dev extras
python -m pip install -e .[dev]

# Confirm CLI is available
gitlog --version

# Generate a dry-run preview
gitlog generate --dry-run

# Traditional Chinese output
gitlog generate --dry-run --lang zh-TW

# HTML format preview
gitlog generate --format html --dry-run

# Commit stats
gitlog stats

# Tweet draft
gitlog tweet
```

PowerShell (Windows):

```powershell
# Clone and enter
git clone https://github.com/JToSound/LogForge.git demo-repo
cd demo-repo

# Install editable with dev extras
python -m pip install -e .[dev]

# Confirm CLI
gitlog --version

# Dry-run
python -m gitlog.cli generate --dry-run

# Or via module
PYTHONPATH=src python -m gitlog generate --dry-run
```

Notes:

- If you see `ModuleNotFoundError` for an unrelated `gitlog` package, uninstall it from your global/user site-packages:

```bash
python -m pip uninstall Gitlog -y
```

- Do not attempt `python -m logforge-gitlog` — module names cannot contain `-` (hyphens). Use `gitlog` instead.