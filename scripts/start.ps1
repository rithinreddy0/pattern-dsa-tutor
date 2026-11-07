$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run python -m venv .venv and install backend/requirements.lock first.' }
Start-Process -WindowStyle Hidden -FilePath $pythonPath -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $projectRoot 'backend') -RedirectStandardOutput (Join-Path $projectRoot 'backend/server.log') -RedirectStandardError (Join-Path $projectRoot 'backend/server-error.log')
Write-Output 'Backend starting at http://127.0.0.1:8000. Start the frontend with: cd frontend; npm run dev'
