# Cron Job Configuration for Automated Football Data Scraper

## For Linux/Mac (Crontab)

### Installation
```bash
# Edit crontab
crontab -e

# Add one of the following lines:
```

### Cron Job Examples

#### Daily at 3 AM
```cron
0 3 * * * cd /path/to/all_leagues_prediction && /path/to/python automated_football_scraper.py >> logs/scraper.log 2>&1
```

#### Weekly on Monday at 2 AM
```cron
0 2 * * 1 cd /path/to/all_leagues_prediction && /path/to/python automated_football_scraper.py >> logs/scraper.log 2>&1
```

#### Twice a week (Monday and Thursday at 3 AM)
```cron
0 3 * * 1,4 cd /path/to/all_leagues_prediction && /path/to/python automated_football_scraper.py >> logs/scraper.log 2>&1
```

### Verify Cron Job
```bash
# List all cron jobs
crontab -l

# Check cron logs
grep CRON /var/log/syslog
```

---

## For Windows (Task Scheduler)

### Method 1: Using PowerShell Script

Save this as `schedule_scraper.ps1`:

```powershell
# Create a scheduled task for the football data scraper

$TaskName = "FootballDataScraper"
$ScriptPath = "C:\\Users\\dagbo_b40tnyc\\OneDrive\\all_leagues _prediction\\automated_football_scraper.py"
$PythonPath = "python.exe"  # Or full path to python.exe
$WorkingDir = "C:\\Users\\dagbo_b40tnyc\\OneDrive\\all_leagues _prediction"

# Create action
$Action = New-ScheduledTaskAction -Execute $PythonPath `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDir

# Create trigger (Daily at 3 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

# Register the task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Automated football data scraper - runs daily at 3 AM"

Write-Host "✓ Scheduled task '$TaskName' created successfully!"
Write-Host "  Schedule: Daily at 3:00 AM"
Write-Host "  Script: $ScriptPath"
```

Run with:
```powershell
# Run as Administrator
powershell -ExecutionPolicy Bypass -File schedule_scraper.ps1
```

### Method 2: Using Task Scheduler GUI

1. Open Task Scheduler (search "Task Scheduler" in Windows)
2. Click "Create Basic Task"
3. Name: "Football Data Scraper"
4. Trigger: Daily at 3:00 AM
5. Action: Start a program
   - Program: `python.exe` (or full path)
   - Arguments: `automated_football_scraper.py`
   - Start in: `C:\\Users\\dagbo_b40tnyc\\OneDrive\\all_leagues _prediction`
6. Finish

### Method 3: Using schtasks command

```cmd
schtasks /create /tn "FootballDataScraper" /tr "python.exe C:\\Users\\dagbo_b40tnyc\\OneDrive\\all_leagues _prediction\\automated_football_scraper.py" /sc daily /st 03:00 /f
```

### Verify Task
```powershell
# List all scheduled tasks
Get-ScheduledTask | Where-Object {$_.TaskName -like "*Football*"}

# Get task details
Get-ScheduledTask -TaskName "FootballDataScraper" | Get-ScheduledTaskInfo

# Run task manually
Start-ScheduledTask -TaskName "FootballDataScraper"
```

---

## For Docker/Cloud Deployments

### Using Docker with cron

Create `Dockerfile.scraper`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY automated_football_scraper.py .
COPY . .

# Install cron
RUN apt-get update && apt-get install -y cron

# Add cron job
RUN echo "0 3 * * * cd /app && python automated_football_scraper.py >> /app/logs/scraper.log 2>&1" > /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron
RUN crontab /etc/cron.d/scraper-cron

CMD ["cron", "-f"]
```

### Using GitHub Actions (Free Cloud Cron)

Create `.github/workflows/scraper.yml`:
```yaml
name: Football Data Scraper

on:
  schedule:
    # Runs daily at 3 AM UTC
    - cron: '0 3 * * *'
  workflow_dispatch:  # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run scraper
        run: |
          python automated_football_scraper.py
      
      - name: Commit and push if changed
        run: |
          git config --global user.name 'GitHub Actions'
          git config --global user.email 'actions@github.com'
          git add data/raw/*.xlsx
          git diff --quiet && git diff --staged --quiet || (git commit -m "Auto-update football data" && git push)
```

---

## Monitoring & Logs

### Check Logs
```bash
# View latest log
tail -f logs/scraper_$(date +%Y%m%d).log

# View all logs
ls -lh logs/

# Search for errors
grep -i error logs/*.log
```

### Email Notifications

Configure in `automated_football_scraper.py`:
```python
def send_email_notification(subject: str, message: str):
    import smtplib
    from email.mime.text import MIMEText
    
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "your-email@gmail.com"
    receiver_email = "your-email@gmail.com"
    password = "your-app-password"  # Use app password for Gmail
    
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
```

---

## Testing

### Test the scraper manually
```bash
# Run once
python automated_football_scraper.py

# Check output
ls -lh data/raw/
ls -lh data/backups/
cat logs/scraper_*.log
```

### Test cron job (Linux/Mac)
```bash
# Run cron job manually
/path/to/python /path/to/automated_football_scraper.py

# Check if cron is running
ps aux | grep cron
```

### Test scheduled task (Windows)
```powershell
# Run task manually
Start-ScheduledTask -TaskName "FootballDataScraper"

# Check task history
Get-ScheduledTask -TaskName "FootballDataScraper" | Get-ScheduledTaskInfo
```

---

## Recommended Schedule

- **During Season (Aug-May):** Daily at 3 AM
- **Off-Season (Jun-Jul):** Weekly on Mondays
- **Match Days:** Twice daily (morning and evening)

---

## Troubleshooting

### Cron job not running
```bash
# Check cron service
sudo service cron status

# Check cron logs
grep CRON /var/log/syslog

# Verify cron syntax
crontab -l
```

### Windows Task not running
```powershell
# Check task status
Get-ScheduledTask -TaskName "FootballDataScraper"

# View task history
Get-ScheduledTaskInfo -TaskName "FootballDataScraper"

# Check Event Viewer
eventvwr.msc
# Navigate to: Task Scheduler > History
```

### Python path issues
```bash
# Use full path to python
which python  # Linux/Mac
where python  # Windows

# Update cron job with full path
0 3 * * * /usr/bin/python3 /full/path/to/automated_football_scraper.py
```
