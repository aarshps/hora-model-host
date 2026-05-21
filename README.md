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
