# LogForge Growth Execution Playbook

This document is the execution guide for increasing project traffic and engagement (stars, issues, discussions).

## 1) One-time setup

1. Install and authenticate GitHub CLI:
   ```powershell
   winget install GitHub.cli
   gh auth login
   ```

2. Run automated growth bootstrap:
   ```powershell
   pwsh -File .\tools\bootstrap_growth.ps1 -Repo JToSound/LogForge -EnableDiscussions -SeedIssues -SeedDiscussion
   ```

3. Confirm repository settings:
   ```powershell
   gh repo view JToSound/LogForge --json name,description,homepageUrl,repositoryTopics,hasDiscussionsEnabled
   gh label list --repo JToSound/LogForge
   gh issue list --repo JToSound/LogForge --state open
   gh discussion list --repo JToSound/LogForge --limit 20
   ```

4. In GitHub web UI, pin:
   - the issue **Tell us your release workflow pain points**
   - the discussion **Show us your changelog workflow**

## 2) Weekly operating loop

### A. Publish and distribute

1. Create a release:
   ```powershell
   git tag -a v0.1.2 -m "v0.1.2 release"
   git push origin v0.1.2
   gh release create v0.1.2 --repo JToSound/LogForge --generate-notes --latest
   ```

2. Post release summary to social channels (X/LinkedIn/Reddit/HN) with CTA:
   - "If useful, star the repo"
   - "Open issue with your workflow pain point"

### B. Community response

1. Triage queue daily:
   ```powershell
   gh issue list --repo JToSound/LogForge --state open
   gh issue list --repo JToSound/LogForge --state open --label "good first issue"
   ```

2. Keep at least:
   - 1 pinned "pain points" issue open
   - 3+ "good first issue" items open

### C. Convert feedback into contributions

1. Convert frequent questions into docs updates.
2. Label new contributor-friendly tasks.
3. Close the loop in each issue with command examples.

## 3) KPI checks (weekly)

Track:
- Repository views
- Unique visitors
- Clone count
- Star conversion (Stars / Views)
- New issues per week
- Discussion activity

Quick checks:
```powershell
gh repo view JToSound/LogForge
gh issue list --repo JToSound/LogForge --state all --limit 50
```

## 4) Manual fallback (if bootstrap script cannot run)

Run each command manually:

```powershell
$repo = "JToSound/LogForge"
gh repo edit $repo --description "AI-powered changelog and release notes generator for developers and teams" --homepage "https://github.com/JToSound/LogForge"
gh repo edit $repo --enable-discussions=true
gh repo edit $repo --add-topic changelog --add-topic release-notes --add-topic conventional-commits --add-topic python --add-topic devtools --add-topic ci-cd --add-topic llm
gh label create "good first issue" --repo $repo --color "7057ff" --description "Good for first-time contributors"
gh label create "help wanted" --repo $repo --color "008672" --description "Community help wanted"
gh label create "bug" --repo $repo --color "d73a4a" --description "Something is not working"
gh label create "feature request" --repo $repo --color "a2eeef" --description "New capability request"
gh label create "question" --repo $repo --color "d876e3" --description "Usage question"
gh label create "docs" --repo $repo --color "0075ca" --description "Documentation improvements"
gh issue create --repo $repo --title "Tell us your release workflow pain points" --body "Share your current release process, biggest pain, and preferred output format." --label "question"
gh issue create --repo $repo --title "good first issue: Improve README onboarding for first-time users" --body "Refine the top README section for faster first run success." --label "good first issue,help wanted,docs"
gh issue create --repo $repo --title "feature request: monorepo component-focused changelog output" --body "Describe required component naming and path filtering behavior for your monorepo." --label "feature request"
gh discussion create --repo $repo --category "General" --title "Show us your changelog workflow" --body "Post your repository type, release cadence, and the release-note pain point you want solved."
```

Then pin one issue and one discussion manually in GitHub web UI.

