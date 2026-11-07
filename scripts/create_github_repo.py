"""Create the requested private repository using Git's cached login, without printing credentials."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

NAME = 'pattern-dsa-tutor'
env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'never'}
result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n', capture_output=True, text=True, env=env)
credential = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
secret = credential.get('password')
if not secret:
    raise SystemExit('No cached GitHub credential. Authenticate Git before retrying.')


def request(path, data=None):
    headers = {'Authorization': f'Bearer {secret}', 'Accept':'application/vnd.github+json', 'User-Agent':'Pattern-DSA-Setup', 'X-GitHub-Api-Version':'2022-11-28'}
    req = urllib.request.Request('https://api.github.com'+path, data=json.dumps(data).encode() if data else None, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


try:
    profile = request('/user')
    if profile['login'] != 'rithinreddy0':
        raise SystemExit('The cached GitHub account differs from the confirmed connected account. No repository was created.')
    try:
        repo = request(f'/repos/{profile["login"]}/{NAME}')
        raise SystemExit('That repository name already exists. No changes made; choose another name or explicitly authorize reuse.')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    repo = request('/user/repos', {'name':NAME, 'description':'Source-grounded DSA learning companion: React, FastAPI, Gemini, PostgreSQL and pgvector.', 'private':True, 'auto_init':False})
    print(json.dumps({'url':repo['html_url'], 'clone_url':repo['clone_url'], 'private':repo['private']}))
except urllib.error.HTTPError as error:
    print(f'GitHub request failed (HTTP {error.code}). No credential values were logged.', file=sys.stderr)
    raise SystemExit(1)
