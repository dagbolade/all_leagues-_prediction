# Ollama Setup Guide for AI Chat Assistant

## What is Ollama?

Ollama is a free, local AI model runner that allows you to run large language models (LLMs) on your own computer. We're using it to power the AI chat assistant with the Qwen model.

## Installation

### Windows

1. **Download Ollama**
   - Visit: https://ollama.com/download
   - Download the Windows installer
   - Run the installer

2. **Verify Installation**
   ```powershell
   ollama --version
   ```

### Linux/Mac

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Installing Qwen Model

Once Ollama is installed, download the Qwen model:

```bash
ollama pull qwen2.5:latest
```

**Alternative models** (if Qwen is too large):
```bash
# Smaller, faster model
ollama pull qwen2.5:7b

# Even smaller
ollama pull qwen2.5:3b

# Or use Llama
ollama pull llama3.2:latest
```

## Starting Ollama

Ollama runs as a background service. To start it:

### Windows
- Ollama starts automatically after installation
- Check system tray for Ollama icon

### Linux/Mac
```bash
ollama serve
```

## Testing Ollama

Test that Ollama is working:

```bash
# Test the model
ollama run qwen2.5:latest

# Type a message and press Enter
# Type /bye to exit
```

## Using with Football Predictor

Once Ollama is running, the AI chat assistant will automatically connect to it.

**Default settings:**
- URL: `http://localhost:11434`
- Model: `qwen2.5:latest`

**To use a different model**, set environment variable:
```bash
# Windows PowerShell
$env:AI_MODEL_NAME="qwen2.5:7b"

# Linux/Mac
export AI_MODEL_NAME="qwen2.5:7b"
```

## Troubleshooting

### "AI assistant is not available"
- Check if Ollama is running: `ollama list`
- Restart Ollama service
- Verify model is downloaded: `ollama list`

### Model is slow
- Use a smaller model (qwen2.5:3b or qwen2.5:7b)
- Close other applications to free up RAM
- Consider using GPU acceleration (automatic if available)

### Connection errors
- Check Ollama is running on port 11434
- Verify firewall isn't blocking localhost connections

## System Requirements

**Minimum:**
- 8GB RAM (for 3B model)
- 4GB disk space

**Recommended:**
- 16GB RAM (for 7B model)
- 8GB disk space
- GPU with 8GB+ VRAM (optional, for faster responses)

## Model Comparison

| Model | Size | RAM Needed | Speed | Quality |
|-------|------|------------|-------|---------|
| qwen2.5:3b | 2GB | 8GB | Fast | Good |
| qwen2.5:7b | 4GB | 16GB | Medium | Better |
| qwen2.5:latest | 8GB | 32GB | Slower | Best |

## Features

Once set up, the AI assistant can:
- ✅ Explain predictions in simple terms
- ✅ Provide betting advice
- ✅ Answer questions about statistics
- ✅ Compare teams and matches
- ✅ Suggest accumulator bets
- ✅ Analyze live matches

## API Endpoints

The AI assistant is available through:
- `/api/ai-chat` - Send messages to AI
- `/chat` - Chat interface page

## Privacy

**All AI processing happens locally on your computer.**
- No data sent to external servers
- Complete privacy
- No API costs
- Works offline (after model download)

## Resources

- Ollama Documentation: https://github.com/ollama/ollama
- Qwen Model Info: https://ollama.com/library/qwen2.5
- Model Library: https://ollama.com/library

---

**Need help?** Check the Ollama documentation or open an issue on GitHub.
