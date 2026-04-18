param(
    [string]$Repo = "JToSound/LogForge",
    [switch]$EnableDiscussions = $true,
    [switch]$SeedIssues = $true,
    [switch]$SeedDiscussion = $true
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Require-Gh {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        $ghDir = Join-Path $env:ProgramFiles "GitHub CLI"
        $ghExe = Join-Path $ghDir "gh.exe"
        if (Test-Path $ghExe) {
            $env:Path = "$ghDir;$env:Path"
        }
    }
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "GitHub CLI (gh) is not installed. Install from https://cli.github.com/"
    }
    gh auth status *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "gh is not authenticated. Run: gh auth login"
    }
}

function Upsert-Label([string]$name, [string]$color, [string]$description) {
    gh label create $name --repo $Repo --color $color --description $description *> $null
    if ($LASTEXITCODE -ne 0) {
        gh label edit $name --repo $Repo --color $color --description $description *> $null
    }
}

function Ensure-Issue([string]$title, [string]$body, [string]$labels) {
    $exists = gh issue list --repo $Repo --search "$title in:title state:open" --json title | ConvertFrom-Json
    if ($exists.Count -eq 0) {
        gh issue create --repo $Repo --title $title --body $body --label $labels *> $null
    }
}

function Ensure-Discussion([string]$title, [string]$body) {
    gh help discussion *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "gh discussion command is not available in this gh build. Skipping discussion seed." -ForegroundColor Yellow
        return
    }
    $exists = gh discussion list --repo $Repo --limit 100 --json title | ConvertFrom-Json
    $found = $exists | Where-Object { $_.title -eq $title }
    if (-not $found) {
        gh discussion create --repo $Repo --category "General" --title $title --body $body *> $null
    }
}

Write-Step "Validating GitHub CLI auth"
Require-Gh

Write-Step "Updating repository metadata"
gh repo edit $Repo `
    --description "AI-powered changelog and release notes generator for developers and teams" `
    --homepage "https://github.com/JToSound/LogForge"

$topics = @(
    "changelog",
    "release-notes",
    "conventional-commits",
    "python",
    "devtools",
    "ci-cd",
    "llm"
)
foreach ($topic in $topics) {
    gh repo edit $Repo --add-topic $topic *> $null
}

if ($EnableDiscussions) {
    Write-Step "Enabling Discussions"
    gh repo edit $Repo --enable-discussions=true
}

Write-Step "Upserting labels"
Upsert-Label "good first issue" "7057ff" "Good for first-time contributors"
Upsert-Label "help wanted" "008672" "Community help wanted"
Upsert-Label "bug" "d73a4a" "Something is not working"
Upsert-Label "feature request" "a2eeef" "New capability request"
Upsert-Label "question" "d876e3" "Usage question"
Upsert-Label "docs" "0075ca" "Documentation improvements"

if ($SeedIssues) {
    Write-Step "Creating seed engagement issues"
    Ensure-Issue `
        "Tell us your release workflow pain points" `
        "Share your current release process, biggest pain, and preferred output format." `
        "question"

    Ensure-Issue `
        "good first issue: Improve README onboarding for first-time users" `
        "Refine the top README section for faster first run success." `
        "good first issue,help wanted,docs"

    Ensure-Issue `
        "feature request: monorepo component-focused changelog output" `
        "Describe required component naming and path filtering behavior for your monorepo." `
        "feature request"
}

if ($EnableDiscussions -and $SeedDiscussion) {
    Write-Step "Creating seed discussion"
    Ensure-Discussion `
        "Show us your changelog workflow" `
        "Post your repository type, release cadence, and the release-note pain point you want solved."
}

Write-Step "Bootstrap complete"
Write-Host "Repository: $Repo" -ForegroundColor Green
Write-Host "Next: pin one issue and one discussion manually in GitHub UI." -ForegroundColor Yellow

