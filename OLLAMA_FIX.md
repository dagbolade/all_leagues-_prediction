# 🔧 Ollama Connection Fix

## Problem
Ollama GUI is running, but the web app can't connect to it.

## Solution

The Ollama GUI app runs independently and doesn't automatically start the API server that the web app needs.

### Fix: Start Ollama API Server

**Option 1: Using Task Manager (Recommended)**
1. Close the Ollama GUI app completely
2. Open PowerShell as **Administrator**
3. Run: `ollama serve`
4. Keep this window open in the background
5. Now the web app will work!

**Option 2: Restart Ollama Service**
1. Close Ollama GUI
2. Search for "Services" in Windows
3. Find "Ollama" service
4. Right-click → Restart
5. The API should now be available

**Option 3: Reinstall/Repair**
Sometimes Ollama doesn't set up the background service correctly:
1. Close Ollama completely
2. Uninstall Ollama
3. Reinstall from: https://ollama.com/download
4. During installation, it should set up the service

### Verify It's Working

Run this in PowerShell:
```powershell
curl http://localhost:11434/api/tags
```

If you see JSON output with models, it's working!

### Then Test the Web App
Visit: http://localhost:5000/chat

The AI should now respond!

---

## Why This Happens

- **Ollama GUI** = Chat interface (what you're using)
- **Ollama API Server** = Background service (what the web app needs)

They're separate! The GUI can work without the API server running.

## Quick Test

```powershell
# Check if API is running
Test-NetConnection -ComputerName localhost -Port 11434
```

If it says "TcpTestSucceeded : True", the API is running!
