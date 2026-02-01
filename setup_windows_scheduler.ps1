# Create a scheduled task for the football data scraper
# Run this script as Administrator

$TaskName = "FootballDataScraper"
$ScriptPath = "C:\Users\dagbo_b40tnyc\OneDrive\all_leagues _prediction\automated_football_scraper.py"
$PythonPath = "python.exe"  # Or specify full path like "C:\Python39\python.exe"
$WorkingDir = "C:\Users\dagbo_b40tnyc\OneDrive\all_leagues _prediction"

Write-Host "="*80
Write-Host "CREATING SCHEDULED TASK FOR FOOTBALL DATA SCRAPER"
Write-Host "="*80

# Create action
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDir

# Create trigger (Daily at 3 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Automated football data scraper - downloads latest data from football-data.co.uk daily at 3 AM" `
        -Force
    
    Write-Host "`n✓ SUCCESS: Scheduled task '$TaskName' created!" -ForegroundColor Green
    Write-Host "  Schedule: Daily at 3:00 AM" -ForegroundColor Cyan
    Write-Host "  Script: $ScriptPath" -ForegroundColor Cyan
    Write-Host "  Working Directory: $WorkingDir" -ForegroundColor Cyan
    
    # Test run option
    Write-Host "`n"
    $response = Read-Host "Would you like to run the task now to test it? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host "`nRunning task..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 3
        
        $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Host "`nTask Status:" -ForegroundColor Cyan
        Write-Host "  Last Run Time: $($taskInfo.LastRunTime)"
        Write-Host "  Last Result: $($taskInfo.LastTaskResult)"
        Write-Host "  Next Run Time: $($taskInfo.NextRunTime)"
    }
    
    Write-Host "`n"
    Write-Host "="*80
    Write-Host "SETUP COMPLETE"
    Write-Host "="*80
    Write-Host "`nTo manage the task:"
    Write-Host "  - Open Task Scheduler (taskschd.msc)"
    Write-Host "  - Or use PowerShell:"
    Write-Host "      Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "      Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "      Stop-ScheduledTask -TaskName '$TaskName'"
    Write-Host "      Unregister-ScheduledTask -TaskName '$TaskName'"
    Write-Host "`n"
    
} catch {
    Write-Host "`n✗ ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nPlease run this script as Administrator" -ForegroundColor Yellow
}
