param(
    [switch]$Open
)

$repoUrl = "https://github.com/JToSound/GitLog"
$issueUrl = "https://github.com/JToSound/GitLog/issues/new/choose"
$discussionUrl = "https://github.com/JToSound/GitLog/discussions"

$xText = @"
From git history to release notes in one command.
LogForge generates Markdown/JSON/HTML + next-version JSON for CI.
$repoUrl

If useful, please star ⭐ and share your release workflow pain points.
"@

$linkedinText = @"
I just shipped updates to LogForge: $repoUrl

It auto-generates changelog/release notes from git history and supports Markdown/JSON/HTML plus CI-friendly next-version JSON.

If your team has a release-note bottleneck, I'd love your feedback:
- Issues: $issueUrl
- Discussions: $discussionUrl
"@

$hnTitle = "Show HN: LogForge - Generate changelogs and release notes from git history"
$hnText = "Built LogForge to remove manual release-note work. Repo: $repoUrl"
$redditTitle = "Open-source: generate changelog + release notes from git history (LogForge)"
$redditText = "Project link: $repoUrl`n`nWhat release workflow pain points should it solve next?"

Add-Type -AssemblyName System.Web
function Encode([string]$text) {
    return [System.Web.HttpUtility]::UrlEncode($text)
}

$links = [ordered]@{
    "X" = "https://twitter.com/intent/tweet?text=$(Encode $xText)"
    "LinkedIn" = "https://www.linkedin.com/feed/?shareActive=true&text=$(Encode $linkedinText)"
    "HackerNews" = "https://news.ycombinator.com/submitlink?u=$(Encode $repoUrl)&t=$(Encode $hnTitle)"
    "Reddit" = "https://www.reddit.com/submit?url=$(Encode $repoUrl)&title=$(Encode $redditTitle)&text=$(Encode $redditText)"
    "GitHub Repo" = $repoUrl
    "GitHub Issues" = $issueUrl
    "GitHub Discussions" = $discussionUrl
}

Write-Host "Distribution links:" -ForegroundColor Cyan
foreach ($entry in $links.GetEnumerator()) {
    Write-Host ("- {0}: {1}" -f $entry.Key, $entry.Value)
    if ($Open) {
        Start-Process $entry.Value
    }
}

Write-Host "`nUse -Open to launch compose pages in browser." -ForegroundColor Yellow

