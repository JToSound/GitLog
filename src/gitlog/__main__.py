"""Module entry point for `python -m gitlog`."""
from __future__ import annotations

from gitlog.cli import app


def main() -> None:
    """Run the Typer CLI application."""
    app()


if __name__ == "__main__":
    main()
