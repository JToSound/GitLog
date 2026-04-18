"""Pydantic v2 data models for gitlog.

These models are deliberately permissive to remain compatible with the
existing test fixtures which pass simplified fields (e.g. `author` as a
string and `date` instead of `timestamp`). Validators normalize legacy
fields into the canonical shapes used across the codebase.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommitType(str, Enum):
    """Semantic commit type categories."""

    FEAT = "feat"
    FIX = "fix"
    PERF = "perf"
    REFACTOR = "refactor"
    DOCS = "docs"
    CHORE = "chore"
    BREAKING = "breaking"
    MISC = "misc"


_CATEGORY_ORDER: list[CommitType] = [
    CommitType.BREAKING,
    CommitType.FEAT,
    CommitType.FIX,
    CommitType.PERF,
    CommitType.REFACTOR,
    CommitType.DOCS,
    CommitType.CHORE,
    CommitType.MISC,
]


class Author(BaseModel):
    """Commit author information."""

    model_config = ConfigDict(extra="allow")

    name: str = ""
    email: str = ""


class Commit(BaseModel):
    """A single git commit.

    The model accepts several legacy constructor shapes used in tests and
    fixtures and normalizes them to the canonical attributes used elsewhere
    in the codebase (e.g. `timestamp`, `author` as an `Author`).
    """

    model_config = ConfigDict(extra="allow")

    sha: str
    short_sha: str | None = None
    message: str
    subject: str = ""
    body: str = ""
    author: Author = Field(default_factory=Author)
    timestamp: datetime | str | None = None
    commit_type: CommitType = CommitType.MISC
    scope: str | None = None
    is_breaking: bool = False
    pr_number: str | None = None
    issue_refs: list[str] = Field(default_factory=list)
    co_authors: list[Author] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    def _normalize_legacy_inputs(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Accept `date` as an alias for `timestamp` (fixtures pass a string).
        if "date" in data and "timestamp" not in data:
            data["timestamp"] = data.pop("date")

        # Allow `author` to be a simple string in fixtures.
        a = data.get("author")
        if isinstance(a, str):
            data["author"] = {"name": a, "email": ""}

        # Populate `short_sha` from `sha` when missing.
        if "sha" in data and "short_sha" not in data:
            try:
                data["short_sha"] = data["sha"][:7]
            except Exception:
                pass

        return data

    @property
    def date(self) -> str | datetime | None:
        """Legacy alias used in tests/fixtures returning the raw timestamp.

        If the timestamp is a datetime, return an ISO string to match prior
        behavior in fixtures that expect string-like dates.
        """
        if isinstance(self.timestamp, datetime):
            return self.timestamp.isoformat()
        return self.timestamp


class Tag(BaseModel):
    """A git version tag."""

    model_config = ConfigDict(extra="allow")

    name: str
    sha: str
    date: datetime | None = None


class ChangelogEntry(BaseModel):
    """Changelog content for a single version.

    Prefer `groups` (mapping from `CommitType` to lists of commits). For
    backward compatibility the model also exposes legacy list attributes.
    """

    model_config = ConfigDict(extra="allow")

    version: str
    date: datetime | None = None
    groups: dict[CommitType, list[Commit]] = Field(default_factory=dict)

    # Legacy convenience fields (kept for compatibility with older code/tests)
    breaking_changes: list[Commit] = Field(default_factory=list)
    features: list[Commit] = Field(default_factory=list)
    fixes: list[Commit] = Field(default_factory=list)
    performance: list[Commit] = Field(default_factory=list)
    refactors: list[Commit] = Field(default_factory=list)
    docs: list[Commit] = Field(default_factory=list)
    misc: list[Commit] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sync_legacy_lists(self) -> ChangelogEntry:
        # If `groups` is populated, fill legacy lists for backward compat.
        if self.groups:
            self.breaking_changes = self.groups.get(CommitType.BREAKING, [])
            self.features = self.groups.get(CommitType.FEAT, [])
            self.fixes = self.groups.get(CommitType.FIX, [])
            self.performance = self.groups.get(CommitType.PERF, [])
            self.refactors = self.groups.get(CommitType.REFACTOR, [])
            self.docs = self.groups.get(CommitType.DOCS, [])
            self.misc = self.groups.get(CommitType.MISC, [])
        return self

    def is_empty(self) -> bool:
        """Return True if entry has no commits."""
        return not any([
            self.breaking_changes, self.features, self.fixes,
            self.performance, self.refactors, self.docs, self.misc,
        ])


class Changelog(BaseModel):
    """Complete changelog with all version entries."""

    model_config = ConfigDict(extra="allow")

    project_name: str = ""
    entries: list[ChangelogEntry] = Field(default_factory=list)
    unreleased: ChangelogEntry | None = None
