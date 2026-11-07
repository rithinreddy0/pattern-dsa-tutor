"""Read-only check of the new repo and existing Render GitHub installation access."""
import json, os, subprocess, urllib.request, urllib.error
env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,env=env)
fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
secret=fields.get('password')
if not secret:raise SystemExit('No saved GitHub login')
def get(path):
    req=urllib.request.Request('https://api.github.com'+path,headers={'Authorization':'Bearer '+secret,'User-Agent':'Pattern-Deployment-Check','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
try:
    repo=get('/repos/rithinreddy0/pattern-dsa-tutor')
    blueprint=get('/repos/rithinreddy0/pattern-dsa-tutor/contents/render-managed.yaml?ref=main')
    print(json.dumps({'repository':repo['html_url'],'private':repo['private'],'repo_id':repo['id'],'blueprint_exists':blueprint.get('type')=='file','blueprint_sha':blueprint.get('sha')}))
    try:
        installs=get('/user/installations')
        matches=[{'id':i['id'],'app':i.get('app_slug'),'selection':i.get('repository_selection')} for i in installs.get('installations',[]) if 'render' in i.get('app_slug','').lower()]
        print(json.dumps({'render_installations':matches}))
    except urllib.error.HTTPError as error:print('Installation access check returned HTTP '+str(error.code))
except urllib.error.HTTPError as error:raise SystemExit('GitHub check returned HTTP '+str(error.code))
