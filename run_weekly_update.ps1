param(
    [string]$Action = "UpdateOnly"
)

$AppPath = "C:\Users\dagbo_b40tnyc\OneDrive\all_leagues _prediction"
$LogFile = "$AppPath\logs\weekly_update.log"

# Ensure logs directory exists
if (-not (Test-Path "$AppPath\logs")) {
    New-Item -ItemType Directory -Force -Path "$AppPath\logs" | Out-Null
}

function Log-Message {
    param([string]$Message)
    $Stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "[$Stamp] $Message" | Out-File -FilePath $LogFile -Append
    Write-Host "[$Stamp] $Message"
}

Log-Message "Starting weekly prediction data automation..."
Set-Location -Path $AppPath

# Check if Python is available
if (-not (Get-Command 'python' -ErrorAction SilentlyContinue)) {
    Log-Message "ERROR: Python not found in PATH."
    exit 1
}

if ($Action -eq "Retrain") {
    Log-Message "Running full data update AND model retrain..."
    $process = Start-Process -FilePath "python" -ArgumentList "update_data.py --retrain" -NoNewWindow -PassThru -Wait
} else {
    Log-Message "Running regular data update..."
    $process = Start-Process -FilePath "python" -ArgumentList "update_data.py" -NoNewWindow -PassThru -Wait
}

if ($process.ExitCode -eq 0) {
    Log-Message "SUCCESS: Update completed."
} else {
    Log-Message "FAILED: Python script exited with code $($process.ExitCode)"
}
