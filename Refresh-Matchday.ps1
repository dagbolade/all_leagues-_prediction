param([switch]$Train, [switch]$SkipXg)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$matchdayPython = Join-Path $PSScriptRoot '.venv-revamp/Scripts/python.exe'
$matchdayCommand = if ($Train) { 'pipeline' } else { 'refresh' }
$matchdayArguments = @('-m','sportslab',$matchdayCommand)
if ($SkipXg) { $matchdayArguments += '--skip-xg' }
& $matchdayPython @matchdayArguments
exit $LASTEXITCODE
