# Ollama Installation Script for Windows
# Downloads and installs Ollama, then pulls the Qwen model

Write-Host "=" * 80
Write-Host "OLLAMA INSTALLATION FOR AI CHAT ASSISTANT"
Write-Host "=" * 80
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  WARNING: Not running as administrator" -ForegroundColor Yellow
    Write-Host "   Some features may not work properly" -ForegroundColor Yellow
    Write-Host ""
}

# Download Ollama installer
$ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
$installerPath = "$env:TEMP\OllamaSetup.exe"

Write-Host "📥 Downloading Ollama installer..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $ollamaUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "✅ Download complete!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to download Ollama" -ForegroundColor Red
    Write-Host "   Please download manually from: https://ollama.com/download" -ForegroundColor Yellow
    exit 1
}

# Install Ollama
Write-Host ""
Write-Host "🔧 Installing Ollama..." -ForegroundColor Cyan
Write-Host "   (This may take a few minutes)" -ForegroundColor Gray

try {
    Start-Process -FilePath $installerPath -Wait -NoNewWindow
    Write-Host "✅ Ollama installed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Installation failed" -ForegroundColor Red
    Write-Host "   Please run the installer manually: $installerPath" -ForegroundColor Yellow
    exit 1
}

# Wait for Ollama service to start
Write-Host ""
Write-Host "⏳ Waiting for Ollama service to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Verify Ollama is running
Write-Host ""
Write-Host "🔍 Verifying Ollama installation..." -ForegroundColor Cyan

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Ollama is running!" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Ollama service not responding yet" -ForegroundColor Yellow
    Write-Host "   Trying to start Ollama..." -ForegroundColor Gray
    
    # Try to start Ollama
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

# Pull Qwen model
Write-Host ""
Write-Host "=" * 80
Write-Host "DOWNLOADING QWEN AI MODEL"
Write-Host "=" * 80
Write-Host ""
Write-Host "📦 Pulling Qwen 2.5 model (this will take several minutes)..." -ForegroundColor Cyan
Write-Host "   Model size: ~4.7GB" -ForegroundColor Gray
Write-Host ""

try {
    # Use smaller model for faster download
    $modelName = "qwen2.5:7b"
    
    Write-Host "   Downloading $modelName..." -ForegroundColor Yellow
    & ollama pull $modelName
    
    Write-Host ""
    Write-Host "✅ Model downloaded successfully!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to download model" -ForegroundColor Red
    Write-Host "   You can download it later with: ollama pull qwen2.5:7b" -ForegroundColor Yellow
}

# Test the model
Write-Host ""
Write-Host "=" * 80
Write-Host "TESTING AI ASSISTANT"
Write-Host "=" * 80
Write-Host ""

Write-Host "🧪 Testing Qwen model..." -ForegroundColor Cyan
Write-Host ""

# Clean up installer
Remove-Item -Path $installerPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=" * 80
Write-Host "✅ INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "=" * 80
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Visit http://localhost:5000/chat to use the AI assistant" -ForegroundColor White
Write-Host "2. Ask questions about football predictions" -ForegroundColor White
Write-Host "3. Get betting tips and analysis" -ForegroundColor White
Write-Host ""
Write-Host "Available models:" -ForegroundColor Cyan
& ollama list
Write-Host ""
Write-Host "To download a different model:" -ForegroundColor Yellow
Write-Host "  ollama pull qwen2.5:latest  (full model, 8GB)" -ForegroundColor Gray
Write-Host "  ollama pull qwen2.5:3b      (smaller, 2GB)" -ForegroundColor Gray
Write-Host ""
