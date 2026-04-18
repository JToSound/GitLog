"""JSON renderer for programmatic consumption."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from gitlog.core.models import Changelog, Commit


class JsonRenderer:
    """Renders a Changelog to a JSON string."""

    def render(self, changelog: Changelog) -> str:
        """Render a Changelog to a pretty-printed JSON string.

        Args:
            changelog: The Changelog to render.

        Returns:
            JSON-formatted string.
        """
        def _commit_to_dict(c: Commit) -> dict[str, Any]:
            return {
                "sha": c.sha,
                "message": c.message,
                "author": getattr(c.author, "name", "") if c.author else "",
                "date": getattr(c, "date", None),
                "scope": c.scope,
                "breaking": c.is_breaking,
                "issues": c.issue_refs,
                "prs": c.pr_number,
            }

        def _serialize_date(d: Any) -> str | None:
            if d is None:
                return None
            if isinstance(d, datetime):
                # Prefer YYYY-MM-DD when the datetime has zeroed time
                if d.hour == 0 and d.minute == 0 and d.second == 0:
                    return d.date().isoformat()
                return d.isoformat()
            if isinstance(d, str):
                return d
            return str(d)

        data = {
            "entries": [
                {
                    "version": entry.version,
                    "date": _serialize_date(entry.date),
                    "groups": {
                        ct.value: [_commit_to_dict(c) for c in commits]
                        for ct, commits in entry.groups.items()
                    },
                }
                for entry in changelog.entries
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
