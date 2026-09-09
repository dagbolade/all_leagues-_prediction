$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$matchdayPython = Join-Path $PSScriptRoot '.venv-revamp/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $matchdayPython)) { throw 'Create .venv-revamp using Python 3.12 and install requirements.txt first.' }
& $matchdayPython -m sportslab serve --port 5000
exit $LASTEXITCODE
