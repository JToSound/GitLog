"""Git log extraction and parsing using GitPython with subprocess fallback.

This implementation prefers GitPython's `Repo` when available (and is
friendly to tests that patch `gitlog.core.git.Repo`). If GitPython is not
installed the parser falls back to calling `git` via subprocess.
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from gitlog.core.models import Author, Commit, CommitType, Tag

# Try to import GitPython's Repo and expose the symbol so tests can patch it.
Repo: Any
try:
    from git import Repo as Repo
except Exception:  # pragma: no cover - absent in some environments
    Repo = None

# Conventional commits regex
_CC_PATTERN = re.compile(
    r"^(?P<type>feat|fix|perf|refactor|docs|chore|test|style|ci|build|revert)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<subject>.+)$",
    re.IGNORECASE,
)
_BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: .+", re.MULTILINE)
_PR_REF = re.compile(r"[Mm]erge (?:pull request|PR) #(\d+)")
_CLOSES_REF = re.compile(r"(?:Closes?|Fixes?|Resolves?) #(\d+)", re.IGNORECASE)
_CO_AUTHOR = re.compile(r"Co-authored-by: (.+?) <(.+?)>", re.IGNORECASE)


class GitLogParser:
    """Parse git history into structured Commit objects.

    Args:
        repo_path: Path to the git repository root. Defaults to cwd.
    """

    def __init__(self, repo_path: Path | None = None) -> None:
        self.repo_path = repo_path or Path.cwd()
        # _repo will be an instance of GitPython's Repo when available.
        self._repo: Any | None = None
        if Repo is not None:
            try:
                self._repo = Repo(self.repo_path)
            except Exception:
                self._repo = None
        self._validate_repo()

    def _validate_repo(self) -> None:
        """Ensure we are inside a git repository."""
        # If we were able to instantiate a Repo object, assume it's valid.
        if self._repo is not None:
            return

        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            cwd=self.repo_path,
        )
        if result.returncode != 0:
            from gitlog.exceptions import GitError

            raise GitError(
                f"Not a git repository: {self.repo_path}",
                hint="Run 'git init' or navigate to a git repository.",
            )

    def get_commits(
        self,
        since: str | None = None,
        until: str | None = None,
        include_body: bool = True,
        include_pr_refs: bool = True,
        paths: list[str] | None = None,
        max_count: int | None = None,
    ) -> list[Commit]:
        """Fetch and parse git commits.

        Args:
            since: Start ref (tag, date, or commit hash).
            until: End ref (tag, date, or commit hash).
            include_body: Whether to fetch commit body text.
            include_pr_refs: Whether to parse PR/Issue references.
            paths: Limit commits to changes in these paths.

        Returns:
            List of parsed Commit objects.
        """
        # Prefer GitPython when available; this makes the parser easier to
        # unit-test (tests patch `gitlog.core.git.Repo`).
        if self._repo is not None:
            rev = None
            if since and until:
                rev = f"{since}..{until}"
            elif since:
                rev = f"{since}..HEAD"
            elif until:
                rev = until

            iter_kwargs: dict[str, Any] = {}
            if paths:
                iter_kwargs["paths"] = paths
            if max_count is not None and max_count > 0:
                iter_kwargs["max_count"] = max_count
            iterator = (
                self._repo.iter_commits(rev, **iter_kwargs)
                if rev
                else self._repo.iter_commits(**iter_kwargs)
            )
            return [self._from_gitpython_commit(c, include_pr_refs) for c in iterator]

        # Fallback to calling `git` directly when GitPython isn't present.
        sep = "\x1E"
        rec_sep = "\x1F"
        fmt = sep.join(["%H", "%h", "%s", "%b", "%aN", "%aE", "%aI", "%D"]) + rec_sep
        cmd = ["git", "log", f"--format={fmt}", "--no-merges"]
        if max_count is not None and max_count > 0:
            cmd.extend(["--max-count", str(max_count)])

        if since and until:
            cmd.append(f"{since}..{until}")
        elif since:
            cmd.append(f"{since}..HEAD")
        elif until:
            cmd.append(until)

        if paths:
            cmd.extend(["--", *paths])

        raw = self._run_git(cmd)
        commits: list[Commit] = []
        for record in raw.split(rec_sep):
            record = record.strip()
            if not record:
                continue
            parts = record.split(sep)
            if len(parts) < 8:
                continue
            try:
                commits.append(self._parse_record(parts, include_pr_refs))
            except Exception:
                continue
        return commits

    def _parse_record(self, parts: list[str], include_pr_refs: bool) -> Commit:
        """Parse a raw git log record into a Commit.

        Args:
            parts: Split git log fields.
            include_pr_refs: Whether to parse PR/Issue refs.

        Returns:
            Parsed Commit object.
        """
        (
            sha,
            short_sha,
            subject,
            body,
            author_name,
            author_email,
            iso_date,
            decorations,
        ) = parts[:8]
        full_message = f"{subject}\n{body}".strip()
        commit_type, scope, is_breaking = self._classify_conventional(subject, body)
        tags = [tag.strip() for tag in re.findall(r"tag:\s*([^,]+)", decorations)]

        pr_number: str | None = None
        issue_refs: list[str] = []
        co_authors: list[Author] = []

        if include_pr_refs:
            pr_match = _PR_REF.search(full_message)
            if pr_match:
                pr_number = pr_match.group(1)
            issue_refs = _CLOSES_REF.findall(full_message)
            for name, email in _CO_AUTHOR.findall(body):
                co_authors.append(Author(name=name.strip(), email=email.strip()))

        return Commit(
            sha=sha, short_sha=short_sha, message=full_message,
            subject=subject, body=body,
            author=Author(name=author_name, email=author_email),
            timestamp=datetime.fromisoformat(iso_date),
            commit_type=commit_type, scope=scope or None,
            is_breaking=is_breaking, pr_number=pr_number,
            issue_refs=issue_refs, co_authors=co_authors, tags=tags,
        )

    def _from_gitpython_commit(self, c: object, include_pr_refs: bool) -> Commit:
        """Convert a GitPython commit-like object into our `Commit` model.

        This helper is deliberately defensive because tests use `MagicMock`
        commit objects with only a subset of attributes set.
        """
        sha = getattr(c, "hexsha", getattr(c, "sha", ""))
        short_sha = sha[:7]
        full_message = getattr(c, "message", "") or ""
        if "\n" in full_message:
            subject, body = full_message.split("\n", 1)
        else:
            subject, body = full_message, ""

        commit_type, scope, is_breaking = self._classify_conventional(subject, body)

        pr_number = None
        issue_refs: list[str] = []
        co_authors: list[Author] = []
        if include_pr_refs:
            pr_match = _PR_REF.search(full_message)
            if pr_match:
                try:
                    pr_number = str(pr_match.group(1))
                except Exception:
                    pr_number = None
            issue_refs = [m for m in _CLOSES_REF.findall(full_message)]
            for name, email in _CO_AUTHOR.findall(body):
                co_authors.append(Author(name=name.strip(), email=email.strip()))

        tags: list[str] = []
        refs_obj = getattr(c, "refs", [])
        if isinstance(refs_obj, (list, tuple, set)):
            for ref in refs_obj:
                ref_name = str(getattr(ref, "name", "")).strip()
                if ref_name and re.match(r"^v?\d+\.\d+", ref_name):
                    tags.append(ref_name)

        author_obj = getattr(c, "author", None)
        author_name = getattr(author_obj, "name", "") or ""
        author_email = getattr(author_obj, "email", "") or ""

        # Ensure we pass plain strings (tests use MagicMock values)
        author_name = str(author_name)
        author_email = str(author_email)

        # committed_date may be an int timestamp; fall back to raw value
        ts = getattr(c, "committed_date", None)
        try:
            timestamp = datetime.fromtimestamp(int(ts)) if ts is not None else None
        except Exception:
            timestamp = ts if ts is not None else None

        return Commit(
            sha=sha,
            short_sha=short_sha,
            message=full_message,
            subject=subject,
            body=body,
            author=Author(name=author_name or "", email=author_email or ""),
            timestamp=timestamp,
            commit_type=commit_type,
            scope=scope or None,
            is_breaking=is_breaking,
            pr_number=pr_number,
            issue_refs=issue_refs,
            co_authors=co_authors,
            tags=tags,
        )

    def _classify_conventional(self, subject: str, body: str) -> tuple[CommitType, str, bool]:
        """Classify a commit using conventional commits pattern.

        Args:
            subject: The commit subject line.
            body: The commit body text.

        Returns:
            Tuple of (CommitType, scope, is_breaking).
        """
        match = _CC_PATTERN.match(subject)
        if not match:
            return CommitType.MISC, "", False

        raw_type = match.group("type").lower()
        scope = match.group("scope") or ""
        is_breaking = bool(match.group("breaking")) or bool(_BREAKING_FOOTER.search(body))

        type_map: dict[str, CommitType] = {
            "feat": CommitType.FEAT, "fix": CommitType.FIX, "perf": CommitType.PERF,
            "refactor": CommitType.REFACTOR, "docs": CommitType.DOCS,
            "chore": CommitType.CHORE, "test": CommitType.MISC,
            "style": CommitType.MISC, "ci": CommitType.CHORE,
            "build": CommitType.CHORE, "revert": CommitType.MISC,
        }
        commit_type = type_map.get(raw_type, CommitType.MISC)
        if is_breaking:
            commit_type = CommitType.BREAKING
        return commit_type, scope, is_breaking

    def get_tags(self) -> list[Tag]:
        """Retrieve all version tags sorted newest first.

        Returns:
            List of Tag objects.
        """
        raw = self._run_git([
            "git", "tag", "--sort=-version:refname",
            "--format=%(refname:short)\x1E%(objectname:short)\x1E%(creatordate:iso)"
        ])
        tags = []
        for line in raw.splitlines():
            parts = line.split("\x1E")
            if len(parts) < 2:
                continue
            name, sha = parts[0].strip(), parts[1].strip()
            date_str = parts[2].strip() if len(parts) > 2 else ""
            date: datetime | None = None
            if date_str:
                try:
                    date = datetime.fromisoformat(date_str)
                except ValueError:
                    pass
            # Only include semver-ish tags
            if re.match(r"^v?\d+\.\d+", name):
                tags.append(Tag(name=name, sha=sha, date=date))
        return tags

    def get_unreleased_commits(self) -> list[Commit]:
        """Get commits since the latest version tag.

        Returns:
            Commits not yet included in any release.
        """
        tags = self.get_tags()
        since = tags[0].name if tags else None
        return self.get_commits(since=since)

    def detect_languages(self) -> list[str]:
        """Auto-detect programming languages in the repository.

        Returns:
            List of detected language names (top 5).
        """
        extensions: dict[str, str] = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
            ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C",
            ".swift": "Swift", ".kt": "Kotlin",
        }
        counts: dict[str, int] = {}
        result = subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, cwd=self.repo_path,
        )
        for fname in result.stdout.splitlines():
            ext = Path(fname).suffix
            if ext in extensions:
                lang = extensions[ext]
                counts[lang] = counts.get(lang, 0) + 1
        return sorted(counts, key=lambda k: -counts[k])[:5]

    def _run_git(self, cmd: list[str]) -> str:
        """Run a git command and return stdout.

        Args:
            cmd: Command list to execute.

        Returns:
            stdout string.

        Raises:
            GitError: If the command fails.
        """
        from gitlog.exceptions import GitError
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.repo_path)
        if result.returncode != 0:
            raise GitError(f"git command failed: {' '.join(cmd)}\n{result.stderr}")
        return result.stdout
