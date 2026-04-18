# External Distribution Runbook

Use this after each meaningful release to drive traffic and interaction.

## 1) Prepare post copy

Use:
- `docs/OUTREACH_COPY_PACK.md`

Pick one platform-specific variant and keep a clear CTA:
- Star the repo
- Open an issue with workflow pain point
- Join Discussions

## 2) Open one-click compose links

```powershell
pwsh -File .\tools\open_distribution_links.ps1
```

To auto-open browser tabs:

```powershell
pwsh -File .\tools\open_distribution_links.ps1 -Open
```

## 3) Posting sequence (recommended)

1. X / Twitter
2. LinkedIn
3. Reddit
4. Hacker News
5. Product Hunt (for bigger milestones)

## 4) Daily follow-up (first 3 days)

```powershell
$ghDir = Join-Path $env:ProgramFiles 'GitHub CLI'
$env:Path = \"$ghDir;$env:Path\"
gh issue list --repo JToSound/LogForge --state open --limit 20
```

Actions:
1. Respond to every new issue/question quickly.
2. Convert good feedback into labeled roadmap issues.
3. Ask commenters to share repository/workflow details.

## 5) Manual tasks that cannot be fully automated cross-platform

1. Submit post on each platform account (X/LinkedIn/Reddit/HN/Product Hunt).
2. Adjust final wording to each community's style rules.
3. Pin/update best-performing post manually where platform supports pinning.

