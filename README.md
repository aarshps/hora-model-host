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

---

## 🔒 Bitwarden Secrets Vault Sync

To conform with strict secrets management across all **Hora** projects, this repository includes an automated utility to securely vault your sensitive files (`.env` and the SSH private key `test_key`) into a `"Hora"` folder in your Bitwarden Vault using the official **Bitwarden CLI** (`bw`).

### Prerequisites
1. **Bitwarden CLI (`bw`)**: Automatically installed locally via npm during workspace optimization.
2. **Logged In**: You must be logged into your Bitwarden account on the CLI:
   ```bash
   bw login
   ```

### Synchronize Local Secrets
Run the PowerShell wrapper script to securely synchronize your `.env` and `test_key` files into your Bitwarden vault:

```powershell
# Execute the sync wrapper
.\deploy\sync_secrets.ps1
```

Or run the Python script directly:
```bash
python deploy/sync_secrets.py
```

### How It Works:
1. Validates that the local `.env` and SSH private key (`test_key`) exist.
2. Prompts you to enter your active `BW_SESSION` key (or automatically grabs it from the environment if already unlocked).
3. Searches your vault for a folder named `"Hora"` (and offers to create it if it does not exist).
4. Synchronizes your `.env` configuration as a Secure Note named `Hora Model Host - Environment Secrets (.env)` inside the `"Hora"` folder.
5. Synchronizes your `test_key` SSH private key as a Secure Note named `Hora Model Host - SSH Private Key (test_key)` inside the `"Hora"` folder.
6. Updates existing items if they already exist, preventing duplicate clutter!

---

## 🎓 End-to-End Architectural Setup & Learning Guide

This section serves as a comprehensive, step-by-step tutorial for developers who want to learn how to set up their own high-performance, secure CPU-only LLM inference endpoints.

### Step 1: Choosing and Provisioning Host Hardware
1. **VPS Selection**: We used a standard **Contabo VPS** powered by **AMD EPYC vCPUs** (6 vCPU, 16 GB RAM, running Ubuntu/Debian). Since the target is a CPU-only environment, selecting a highly optimized model is paramount.
2. **Architecture Check**: Running `lscpu` reveals the CPU flags. AMD EPYC processors support AVX2 and SHA extensions, which allow modern neural networks to execute highly efficiently on CPUs without requiring expensive Nvidia GPUs.

### Step 2: High-Performance Local Inference Backend (Ollama)
1. **Native Installation**: Ollama is installed natively on the VPS to exploit all available CPU vector pipelines.
2. **Model Selection**: We pulled the highly optimized **Gemma 4 e4b** model (`gemma4:e4b`). This is a 4-bit quantized version of Google's state-of-the-art Gemma model. It operates exceptionally well within CPU speed constraints:
   * **Cold Start Load Time**: ~50s - 2m (the time it takes Ollama to copy 9.6 GB of neural weights into system RAM).
   * **Active Speed**: **9.13 tokens per second** (more than fast enough for interactive chat and developer workflows!).
3. **Internal Configuration**: Ollama listens on `127.0.0.1:11434` (localhost). We keep this port tightly blocked from the outside world.

### Step 3: Designing the FastAPI Reverse Proxy Gateway
A raw Ollama port is insecure (no built-in auth, vulnerable to DDoS or unauthorized usage). We designed a robust, lightweight gatekeeper service using **FastAPI** (`gateway/main.py`):
1. **Bearer Authentication**: Validates every incoming HTTP request header against a secure `API_KEY` stored in `.env`.
2. **Discovery Support (Critical for Clients)**: Standard LLM clients (like OpenAI SDKs, LangChain, or OpenCode plugins) often execute unauthenticated "pre-flight" checks (like hitting the root `/` or `/v1` to verify if the server is alive). We deployed public endpoints `/` and `/v1` that return quick, unauthenticated responses, eliminating timeout hangs in custom clients while protecting the core generation endpoints behind Bearer checks.
3. **Streaming Direct-Pass**: Using `httpx.AsyncClient`, the gateway opens an asynchronous, persistent stream to Ollama's native endpoint and pipes the chunks back to the client in real-time, maintaining high-fidelity event-streaming (`text/event-stream`).

### Step 4: Systemd Service Daemonization
To guarantee high availability and automated recovery, both components are configured as systemd service daemons:
* **Gateway Daemon (`/etc/systemd/system/gateway.service`)**:
  ```ini
  [Unit]
  Description=Hora Model Host API Gateway
  After=network.target

  [Service]
  User=root
  WorkingDirectory=/opt/hora-model-host
  ExecStart=/opt/hora-model-host/venv/bin/uvicorn gateway.main:app --host 0.0.0.0 --port 8000
  Restart=always
  EnvironmentFile=/opt/hora-model-host/.env

  [Install]
  WantedBy=multi-user.target
  ```
Whenever the VPS restarts, or if the python process encounters a runtime exception, systemd instantly restarts the gateway.

### Step 5: Network Security & Firewall Rules
1. **Strict Port Separation**: 
   * Public: Port `8000` (FastAPI security proxy) is opened publicly to accept client requests.
   * Private: Port `11434` (raw Ollama engine) is left completely closed to external network interfaces.
2. **UFW (Uncomplicated Firewall) Configuration**:
   ```bash
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow 22/tcp    # SSH
   ufw allow 8000/tcp  # Secure FastAPI Gateway
   ufw enable
   ```

### Step 6: Client Integration (e.g., OpenCode TUI)
For developer workflows, the hosted model is connected to standard terminal clients:
1. Define a custom provider utilizing the `@ai-sdk/openai-compatible` standard.
2. Point the base URL to our public proxy: `http://185.194.218.92:8000/v1`.
3. Provide the secure Bearer token as the credential key.
4. Interact in real-time with full streaming completion.

### 💡 Summary of Key Developer Lessons Learned:
* **The "Pre-flight Check" Traps**: Many standard OpenAI-compatible libraries do not pass headers when doing basic server checks. If your API gatekeeper blocks the root `/` with a `401 Unauthorized`, standard packages will instantly fail to initiate a connection. Ensure your root `/` and `/v1` endpoints are publicly accessible and return standard JSON structure.
* **CPU Ram Lifecycles (Keep-Alive)**: Ollama unloads inactive models from memory after 5 minutes by default. In a production pipeline, set `OLLAMA_KEEP_ALIVE=-1` in the systemd configuration file so the model is permanently resident in RAM, completely avoiding cold-start latency.
* **Environment Paths**: Standard package managers (like `npm`) sometimes call nested CLI dependencies (like `node`). If your subprocess environment lacks explicit path access to the node runtime, hooks will crash. Always construct a clean environment path before launching automated scripts.
