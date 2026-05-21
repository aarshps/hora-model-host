# Hora Model Host

This repository holds the deployment harness and secure API gateway for hosting Google's **Gemma 4 LLM** natively on a Contabo VPS. The API is exposed as a secure public endpoint with full OpenAI-compatible API endpoints behind an API key check.

## Architecture

- **Ollama Backend**: Runs locally on the VPS, handling high-performance AMD EPYC CPU-optimized execution of **Gemma 4 (e4b)**.
- **FastAPI Reverse Proxy Gateway**: Intercepts requests, validates the `Authorization: Bearer <API_KEY>` header, and streams client requests straight to Ollama's OpenAI-compatible routes.
- **Systemd Management**: Both Ollama and the FastAPI gateway are run as robust systemd services, handling automatic restarts and recovery.

---

## Directory Structure

```
hora-model-host/
  ├── gateway/
  │    ├── __init__.py
  │    ├── main.py          # FastAPI application
  │    ├── requirements.txt # Python dependencies
  │    └── config.py        # Environment variables parser
  ├── deploy/
  │    ├── install.sh       # Unified VPS install script
  │    └── gateway.service  # Systemd service unit template
  ├── .env.example          # Sample environment configurations
  ├── .gitignore            # Git ignore list (protecting env secrets)
  └── README.md             # This file
```

---

## Quick Start & Usage

To communicate with the secure endpoint, pass your API key as a Bearer token in the `Authorization` header.

### cURL Example
```bash
curl -X POST http://185.194.218.92:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_SECRET_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:e4b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'
```

### Python OpenAI Client
```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_SECRET_API_KEY",
    base_url="http://185.194.218.92:8000/v1"
)

response = client.chat.completions.create(
    model="gemma4:e4b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum physics in one sentence."}
    ],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

---

## OpenCode TUI Integration

You can natively test and use our secure remote Gemma 4 instance via [OpenCode](https://opencode.ai), a premium, state-of-the-art terminal-based AI assistant.

### 1. Configure Provider (`~/.config/opencode/opencode.json`)
Add the custom `hora-gemma` provider to your global OpenCode config:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "hora-gemma/gemma4:e4b",
  "provider": {
    "hora-gemma": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Hora Gemma 4",
      "options": {
        "baseURL": "http://185.194.218.92:8000/v1",
        "timeout": 600000,
        "chunkTimeout": 60000
      },
      "models": {
        "gemma4:e4b": {
          "name": "Gemma 4 (4B)"
        }
      }
    }
  }
}
```

### 2. Configure Credentials (`~/.local/share/opencode/auth.json`)
Add the secure Bearer API Key matching the custom provider name:

```json
{
  "hora-gemma": {
    "type": "api",
    "key": "hora_live_8e94a7cb2c114f0c9780a1d3fbc9581f"
  }
}
```

### 3. Run directly!
```bash
# Direct command completion check:
opencode run "Hello! Tell me a one-sentence greeting." --model hora-gemma/gemma4:e4b --pure --dangerously-skip-permissions

# Full interactive chat session:
opencode run --model hora-gemma/gemma4:e4b --pure --dangerously-skip-permissions
```
