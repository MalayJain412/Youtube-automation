$ErrorActionPreference = "Stop"

# Ensure relative paths resolve from repo root
Set-Location -Path $PSScriptRoot

# Activate venv if present
if (Test-Path "./venv/Scripts/Activate.ps1") {
  . ./venv/Scripts/Activate.ps1
}

python -m uvicorn ytautomation.api.main:app --host 127.0.0.1 --port 8002
