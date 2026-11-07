"""Read a key through stdin, save to the OS credential vault, and verify with Google."""
import json
import sys
import keyring
import httpx
import getpass

print('Ready for API key on stdin. Input is not logged.', flush=True)
secret = getpass.getpass('Gemini API key (hidden): ').strip()
if len(secret) < 20:
    raise SystemExit('The provided key appears incomplete. Nothing was stored.')
backend = keyring.get_keyring()
if 'Windows' not in type(backend).__name__ and 'WinVault' not in type(backend).__name__:
    raise SystemExit('Windows Credential Manager is unavailable; refusing plaintext storage.')
keyring.set_password('pattern-dsa-tutor', 'gemini-api-key', secret)
print('Stored in Windows Credential Manager. No key written to project files.', flush=True)
try:
    response = httpx.get('https://generativelanguage.googleapis.com/v1beta/models', headers={'x-goog-api-key':secret}, timeout=30)
    if response.status_code != 200:
        print(json.dumps({'google_accepted_key':False,'http_status':response.status_code}))
        raise SystemExit(2)
    models = response.json().get('models', [])
    generators = [m['name'].removeprefix('models/') for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]
    embedders = [m['name'].removeprefix('models/') for m in models if 'embedContent' in m.get('supportedGenerationMethods', [])]
    print(json.dumps({'google_accepted_key':True,'generation_models':generators,'embedding_models':embedders}))
except httpx.HTTPError:
    print('Stored securely. Google verification could not complete due to a network error.')
    raise SystemExit(3)
