"""Twitter/X announcement draft renderer."""
from __future__ import annotations

from gitlog.core.models import ChangelogEntry, CommitType


class TwitterRenderer:
    """Generates a concise Twitter/X announcement from a ChangelogEntry."""

    def __init__(self, model: str = "gpt-4o-mini", project_name: str = "") -> None:
        self._model = model
        self._project_name = project_name

    def render(self, entry: ChangelogEntry) -> str:
        """Generate a tweet-length announcement for a release.

        Args:
            entry: The ChangelogEntry to announce.

        Returns:
            A string ≤ 280 characters suitable for Twitter/X.
        """
        feats = entry.groups.get(CommitType.FEAT, [])
        fixes = entry.groups.get(CommitType.FIX, [])
        breaking = entry.groups.get(CommitType.BREAKING, [])

        summary_lines = []
        if breaking:
            summary_lines.append(f"⚠️ BREAKING: {breaking[0].message[:60]}")
        for c in feats[:3]:
            summary_lines.append(f"✨ {c.message[:70]}")
        for c in fixes[:2]:
            summary_lines.append(f"🐛 {c.message[:70]}")

        fallback = (
            f"🚀 {self._project_name or 'App'} {entry.version} released!\n"
            + "\n".join(summary_lines[:4])
        )

        try:
            import litellm

            bullets = "\n".join(summary_lines[:6]) or "General improvements."
            prompt = (
                f"Write a Twitter/X announcement for {self._project_name or 'software'} "
                f"version {entry.version}.\n"
                f"Key changes:\n{bullets}\n"
                "Requirements: <= 280 chars, engaging, include version, use 1-2 emojis."
            )
            resp = litellm.completion(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text[:280]
        except Exception:  # noqa: BLE001
            return fallback[:280]
