"""Publish only the new, user-approved repository. Never prints credentials."""
import json, os, subprocess, urllib.request
env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,env=env)
credential=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
secret=credential.get('password')
if not secret:raise SystemExit('No saved GitHub login')
path='https://api.github.com/repos/rithinreddy0/pattern-dsa-tutor'
headers={'Authorization':'Bearer '+secret,'User-Agent':'Pattern-Deploy','Accept':'application/vnd.github+json'}
with urllib.request.urlopen(urllib.request.Request(path,headers=headers),timeout=30) as response:repo=json.load(response)
if repo['id']!=1449583112 or repo['full_name']!='rithinreddy0/pattern-dsa-tutor':raise SystemExit('Repository identity mismatch')
req=urllib.request.Request(path,method='PATCH',headers=headers,data=json.dumps({'private':False}).encode())
with urllib.request.urlopen(req,timeout=30) as response:updated=json.load(response)
print(json.dumps({'repository':updated['html_url'],'visibility':updated['visibility']}))
