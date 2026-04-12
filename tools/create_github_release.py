#!/usr/bin/env python3
"""Create PR and GitHub Release and upload dist assets.

Usage: ensure GITHUB_TOKEN is set in the environment, then run:
  python tools/create_github_release.py

The script will:
- create a PR from release/v0.1.1 -> main (if not existing)
- create a Release for tag v0.1.1 (if not existing)
- upload dist/logforge_gitlog-0.1.1* assets to the Release
"""

import os
import sys
import subprocess
from pathlib import Path
import json

try:
    import requests
    import mimetypes
except Exception as exc:
    print("Missing dependency 'requests'. Install with: python -m pip install requests", file=sys.stderr)
    sys.exit(2)


def get_remote_owner_repo():
    try:
        url = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
    except subprocess.CalledProcessError as e:
        print("Failed to get git remote origin:", e, file=sys.stderr)
        sys.exit(1)
    # parse
    if url.startswith("git@"):
        # git@github.com:owner/repo.git
        try:
            _, path = url.split(":", 1)
        except ValueError:
            path = url
    elif url.startswith("http://") or url.startswith("https://"):
        # https://github.com/owner/repo.git
        parts = url.split("/")
        path = "/".join(parts[3:]) if len(parts) >= 4 else parts[-1]
    else:
        path = url
    if path.endswith('.git'):
        path = path[:-4]
    if path.startswith('/'):
        path = path[1:]
    if '/' not in path:
        print(f"Unable to parse owner/repo from remote url '{url}'", file=sys.stderr)
        sys.exit(1)
    owner, repo = path.split('/', 1)
    return owner, repo


def read_optional_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding='utf-8')
    return ''


def main():
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if not token:
        print('GITHUB_TOKEN (or GH_TOKEN) not set in the environment.', file=sys.stderr)
        sys.exit(2)

    owner, repo = get_remote_owner_repo()
    api_base = f'https://api.github.com/repos/{owner}/{repo}'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'logforge-release-script'
    }

    repo_root = Path(__file__).resolve().parents[1]
    pr_md = repo_root / 'release_pr.md'
    release_draft_md = repo_root / 'GITHUB_RELEASE_DRAFT.md'
    fallback_release_notes = repo_root / 'RELEASE_NOTES_v0.1.0.md'

    pr_title = f'chore(release): v0.1.1'
    pr_body = read_optional_file(pr_md) or ''
    release_body = read_optional_file(release_draft_md) or read_optional_file(fallback_release_notes) or pr_body

    head = 'release/v0.1.1'
    base = 'main'

    # Create PR if not exists
    print('Creating or locating PR...')
    pr_url = f'{api_base}/pulls'
    payload = {
        'title': pr_title,
        'head': head,
        'base': base,
        'body': pr_body,
        'maintainer_can_modify': True,
    }
    r = requests.post(pr_url, headers=headers, json=payload)
    if r.status_code == 201:
        pr = r.json()
        print('PR created:', pr.get('html_url'))
    else:
        # Possibly already exists
        if r.status_code == 422:
            checks_url = f"{api_base}/pulls?head={owner}:{head}&state=all"
            rr = requests.get(checks_url, headers=headers)
            if rr.status_code == 200 and rr.json():
                pr = rr.json()[0]
                print('Existing PR found:', pr.get('html_url'))
            else:
                print('Failed to create PR (422) and no existing PR found. Response:', r.text, file=sys.stderr)
        else:
            print(f'Failed to create PR: {r.status_code} {r.text}', file=sys.stderr)

    # Create or get Release
    tag = 'v0.1.1'
    print('Creating or locating Release for tag', tag)
    get_rel = requests.get(f'{api_base}/releases/tags/{tag}', headers=headers)
    if get_rel.status_code == 200:
        rel = get_rel.json()
        print('Existing release found:', rel.get('html_url'))
    else:
        rel_payload = {
            'tag_name': tag,
            'name': tag,
            'body': release_body,
            'draft': False,
            'prerelease': False,
        }
        r2 = requests.post(f'{api_base}/releases', headers=headers, json=rel_payload)
        if r2.status_code in (200, 201):
            rel = r2.json()
            print('Release created:', rel.get('html_url'))
        else:
            print('Failed to create release:', r2.status_code, r2.text, file=sys.stderr)
            sys.exit(1)

    upload_url_template = rel.get('upload_url')
    if not upload_url_template:
        print('No upload_url returned by release API', file=sys.stderr)
        sys.exit(1)

    # Upload assets
    dist_dir = repo_root / 'dist'
    if not dist_dir.exists():
        print('Dist directory not found:', dist_dir, file=sys.stderr)
        sys.exit(1)

    files_to_upload = sorted([p for p in dist_dir.iterdir() if p.is_file() and '0.1.1' in p.name])
    if not files_to_upload:
        print('No distribution files matching 0.1.1 found in dist/', file=sys.stderr)
        sys.exit(1)

    for p in files_to_upload:
        name = p.name
        upload_url = upload_url_template.replace('{?name,label}', '') + f'?name={name}'
        mime_type, _ = mimetypes.guess_type(str(p))
        headers_asset = {
            'Authorization': f'token {token}',
            'Content-Type': mime_type or 'application/octet-stream',
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'logforge-release-script'
        }
        print('Uploading', name)
        with p.open('rb') as fh:
            data = fh.read()
        rr = requests.post(upload_url, headers=headers_asset, data=data)
        if rr.status_code in (200, 201):
            print('Uploaded', name)
        else:
            print('Failed to upload', name, rr.status_code, rr.text, file=sys.stderr)

    print('Done.')


if __name__ == '__main__':
    main()
