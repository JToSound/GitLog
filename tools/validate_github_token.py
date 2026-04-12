#!/usr/bin/env python3
"""Validate GITHUB_TOKEN presence and scopes.

Prints one of:
 - NOT_SET
 - OK <login> <scopes>
 - ERROR <status> <message>

Exit codes:
 - 0 -> OK
 - 1 -> ERROR (invalid)
 - 2 -> NOT_SET
"""

import os
import sys

try:
    import requests
except Exception:
    print("Missing dependency 'requests'. Install with: python -m pip install requests", file=sys.stderr)
    sys.exit(2)

token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
if not token:
    print('NOT_SET')
    sys.exit(2)

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'logforge-token-check'
}

try:
    r = requests.get('https://api.github.com/user', headers=headers, timeout=10)
except Exception as exc:
    print('ERROR', 'request-failed', str(exc))
    sys.exit(1)

if r.ok:
    try:
        jd = r.json()
    except Exception:
        jd = {}
    login = jd.get('login') or ''
    scopes = r.headers.get('x-oauth-scopes') or ''
    print('OK', login, scopes)
    sys.exit(0)
else:
    try:
        msg = r.json().get('message')
    except Exception:
        msg = r.text[:200]
    print('ERROR', r.status_code, msg)
    sys.exit(1)
