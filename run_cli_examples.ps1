$ErrorActionPreference = "Stop"

if (Test-Path "./venv/Scripts/Activate.ps1") {
  . ./venv/Scripts/Activate.ps1
}

python -m ytautomation.cli run-all --csv data/input/topics.csv
