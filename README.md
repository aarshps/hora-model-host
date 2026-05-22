# Hora Model Host

> A complete, production-ready deployment harness for hosting Google's **Gemma 4 LLM** on a CPU-only VPS, exposed as a secure, OpenAI-compatible public API behind a FastAPI reverse proxy gateway — with full Bitwarden vault integration and OpenCode TUI support.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)]()
[![Ollama](https://img.shields.io/badge/Ollama-latest-orange.svg)]()

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Dependencies](#dependencies)
- [Repository Structure](#repository-structure)
- [Quick Start (Consuming the API)](#quick-start-consuming-the-api)
- [End-to-End Setup Guide](#end-to-end-setup-guide)
  - [Phase 1: VPS Provisioning](#phase-1-vps-provisioning)
  - [Phase 2: Ollama & Model Setup](#phase-2-ollama--model-setup)
  - [Phase 3: Gateway Deployment](#phase-3-gateway-deployment)
  - [Phase 4: Firewall & Security](#phase-4-firewall--security)
  - [Phase 5: Verification](#phase-5-verification)
- [Client Integration](#client-integration)
  - [cURL](#curl-example)
  - [Python OpenAI SDK](#python-openai-sdk)
  - [Node.js OpenAI SDK](#nodejs-openai-sdk)
  - [OpenCode TUI](#opencode-tui-integration)
- [Bitwarden Secrets Vault Sync](#bitwarden-secrets-vault-sync)
- [Operations & Troubleshooting](#operations--troubleshooting)
- [Performance Benchmarks](#performance-benchmarks)
- [Lessons Learned](#lessons-learned)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTERNET                                │
│                                                                 │
│   [Any OpenAI-compatible Client]                                │
│        curl / Python SDK / Node SDK / OpenCode TUI              │
│                           │                                     │
│                   Authorization: Bearer <KEY>                   │
└───────────────────────────┼─────────────────────────────────────┘
                            │ Port 8000 (Public)
┌───────────────────────────┼─────────────────────────────────────┐
│                    CONTABO VPS (185.194.218.92)                  │
│                           │                                     │
│              ┌────────────▼────────────────┐                    │
│              │   FastAPI Gateway (Uvicorn) │                    │
│              │   - Bearer Auth Validation  │                    │
│              │   - Async Stream Proxy      │                    │
│              │   - CORS Middleware         │                    │
│              └────────────┬────────────────┘                    │
│                           │ localhost:11434 (Private)            │
│              ┌────────────▼────────────────┐                    │
│              │     Ollama Daemon           │                    │
│              │   - Gemma 4 E4B (9.6 GB)   │                    │
│              │   - CPU AVX2 Optimized      │                    │
│              └─────────────────────────────┘                    │
│                                                                 │
│   [UFW Firewall]                                                │
│     ✅ Port 8000/tcp  → Public (Gateway)                        │
│     ✅ Port 22/tcp    → SSH                                     │
│     ❌ Port 11434/tcp → Blocked (Ollama internal only)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependencies

### 🖥️ VPS Server-Side (Remote Host)

| Dependency | Version | Purpose | Install Command |
|---|---|---|---|
| **Ubuntu/Debian** | 24.04 LTS | Host operating system | — |
| **Python** | 3.12+ | Gateway runtime | `apt install python3 python3-venv python3-pip` |
| **Ollama** | latest | LLM inference engine | `curl -fsSL https://ollama.com/install.sh \| sh` |
| **systemd** | built-in | Service management | Pre-installed on Ubuntu |
| **UFW** | built-in | Firewall | `apt install ufw` |
| **curl, git** | latest | Utilities | `apt install curl git` |

**Python packages** (installed in venv via `gateway/requirements.txt`):

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | ≥0.110.0 | API framework for the gateway |
| `uvicorn` | ≥0.28.0 | ASGI server |
| `httpx` | ≥0.27.0 | Async HTTP client for reverse proxying to Ollama |
| `python-dotenv` | ≥1.0.1 | `.env` file loader |

### 💻 Local Developer Workstation

| Dependency | Version | Purpose | Install |
|---|---|---|---|
| **Git** | latest | Version control | [git-scm.com](https://git-scm.com) |
| **Python** | 3.12+ | Running deploy/sync scripts | [python.org](https://python.org) |
| **Node.js** | 18+ | Required by Bitwarden CLI & OpenCode | [nodejs.org](https://nodejs.org) |
| **npm** | 10+ | Package manager for Node.js tools | Bundled with Node.js |
| **Bitwarden CLI** | latest | Secrets vault management | `npm install -g @bitwarden/cli` |
| **OpenCode** | latest | Terminal-based AI assistant (optional) | [opencode.ai/download](https://opencode.ai/download) |
| **SSH client** | built-in | VPS access | Pre-installed on Windows/macOS/Linux |

### ☁️ Third-Party Services

| Service | Purpose | Required? |
|---|---|---|
| **VPS provider** (e.g. Contabo) | Remote host for Ollama + Gateway | ✅ Yes |
| **GitHub** | Repository and wiki hosting | ✅ Yes |
| **Bitwarden** | Encrypted secrets vault | 🟡 Recommended |

---

## Repository Structure

```
hora-model-host/
├── gateway/                      # FastAPI Gateway Application
│   ├── __init__.py               # Python package marker
│   ├── main.py                   # FastAPI app with auth, proxy, discovery endpoints
│   ├── config.py                 # Environment variables parser (dotenv)
│   └── requirements.txt          # Python dependencies for the gateway
├── deploy/                       # Deployment & Operations Scripts
│   ├── install.sh                # One-shot VPS bootstrap script (Ollama + Gateway + systemd)
│   ├── gateway.service           # Systemd unit file template
│   ├── sync_secrets.py           # Bitwarden vault sync utility (Python)
│   └── sync_secrets.ps1          # PowerShell wrapper for vault sync
├── .env                          # 🔒 LOCAL ONLY - secrets (gitignored)
├── .env.example                  # Template showing required environment variables
├── .gitignore                    # Protects .env, SSH keys, reports from commits
├── test_key / test_key.pub       # 🔒 LOCAL ONLY - SSH keypair for VPS (gitignored)
├── performance_report.md         # 🔒 LOCAL ONLY - benchmark results (gitignored)
├── agent_skills.md               # AI agent knowledge transfer manual
└── README.md                     # This file
```

### Environment Variables Reference

| Variable | Description | Example |
|---|---|---|
| `PORT` | Gateway listen port | `8000` |
| `OLLAMA_BASE_URL` | Internal Ollama endpoint | `http://localhost:11434` |
| `API_KEY` | Bearer authentication token | `hora_live_8e94a7cb...` |
| `GEMMA_MODEL` | Ollama model identifier | `gemma4:e4b` |
| `BW_PASSWORD` | Bitwarden master password (for vault sync) | `your_master_password` |

---

## Quick Start (Consuming the API)

If the gateway is already deployed and you just want to **use** the API:

### cURL Example
```bash
curl -X POST http://185.194.218.92:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
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

### Python OpenAI SDK
```bash
pip install openai
```
```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
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

### Node.js OpenAI SDK
```bash
npm install openai
```
```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
  baseURL: 'http://185.194.218.92:8000/v1',
  apiKey: 'YOUR_API_KEY',
});

async function main() {
  const stream = await openai.chat.completions.create({
    model: 'gemma4:e4b',
    messages: [{ role: 'user', content: 'What is 15 * 15?' }],
    stream: true,
  });
  for await (const chunk of stream) {
    process.stdout.write(chunk.choices[0]?.delta?.content || '');
  }
}
main();
```

---

## End-to-End Setup Guide

Follow these steps to replicate this entire setup from scratch on your own VPS.

### Phase 1: VPS Provisioning

1. **Provision a VPS** with at least 6 vCPU, 16 GB RAM, and 100 GB SSD (e.g., [Contabo VPS M](https://contabo.com)). For hosting frontier reasoning or MoE models, 12 vCPU and 48 GB RAM (e.g., Contabo VPS XL) is recommended.
2. **Choose Ubuntu 24.04 LTS** as the operating system.
3. **Note your server's public IP address** (e.g., `185.194.218.92`).
4. **Generate an SSH keypair** for secure access:
   ```bash
   ssh-keygen -t rsa -b 2048 -f ./test_key -N ""
   ```
5. **Copy the public key** to the VPS:
   ```bash
   ssh-copy-id -i ./test_key.pub root@YOUR_VPS_IP
   ```
6. **Verify CPU capabilities** (should show AVX2 support):
   ```bash
   ssh -i ./test_key root@YOUR_VPS_IP "lscpu | grep -i avx"
   ```

### Phase 2: Ollama & Model Setup

1. **SSH into the VPS**:
   ```bash
   ssh -i ./test_key root@YOUR_VPS_IP
   ```
2. **Install system dependencies**:
   ```bash
   apt update -y && apt install -y python3 python3-venv python3-pip curl git
   ```
3. **Install Ollama**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
4. **Enable and start Ollama**:
   ```bash
   systemctl enable ollama && systemctl start ollama
   ```
5. **Pull the Gemma 4 model** (this takes 5-15 minutes depending on network speed):
   ```bash
   ollama pull gemma4:e4b
   ```
6. **Verify the model is available**:
   ```bash
   ollama list
   curl http://localhost:11434/v1/models
   ```

### Phase 3: Gateway Deployment

1. **Clone this repository onto the VPS**:
   ```bash
   mkdir -p /opt/hora-model-host
   cd /opt/hora-model-host
   git clone https://github.com/YOUR_USER/hora-model-host.git .
   ```
   Or use SFTP to upload files from your local machine.

2. **Create the Python virtual environment**:
   ```bash
   python3 -m venv /opt/hora-model-host/venv
   /opt/hora-model-host/venv/bin/pip install --upgrade pip
   /opt/hora-model-host/venv/bin/pip install -r gateway/requirements.txt
   ```

3. **Create the `.env` configuration**:
   ```bash
   cat <<EOF > /opt/hora-model-host/.env
   PORT=8000
   OLLAMA_BASE_URL=http://localhost:11434
   API_KEY=$(python3 -c "import secrets; print(f'hora_live_{secrets.token_hex(16)}')")
   GEMMA_MODEL=gemma4:e4b
   EOF
   chmod 600 /opt/hora-model-host/.env
   cat /opt/hora-model-host/.env   # Note your generated API_KEY!
   ```

4. **Install the systemd service**:
   ```bash
   cp deploy/gateway.service /etc/systemd/system/gateway.service
   systemctl daemon-reload
   systemctl enable gateway
   systemctl start gateway
   ```

5. **Verify the service is running**:
   ```bash
   systemctl status gateway
   journalctl -u gateway -f -n 20
   ```

### Phase 4: Firewall & Security

1. **Configure UFW**:
   ```bash
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow 22/tcp       # SSH access
   ufw allow 8000/tcp     # FastAPI Gateway (public)
   # Do NOT allow 11434 — Ollama must stay internal
   ufw enable
   ```

2. **Verify firewall rules**:
   ```bash
   ufw status verbose
   ```

### Phase 5: Verification

From your **local machine**, test all endpoints:

```bash
# 1. Health check (public, no auth)
curl http://YOUR_VPS_IP:8000/health

# 2. Root discovery (public, no auth)
curl http://YOUR_VPS_IP:8000/

# 3. Rejected request (no API key → 401)
curl -X POST http://YOUR_VPS_IP:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:e4b","messages":[{"role":"user","content":"Hi"}]}'

# 4. Authenticated request (valid API key → 200)
curl -X POST http://YOUR_VPS_IP:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:e4b","messages":[{"role":"user","content":"Say hello in one word."}],"stream":false}'
```

> ⚠️ **First request may take 1-2 minutes** as Ollama loads the 9.6 GB model into RAM. Subsequent requests respond in <1 second.

---

## OpenCode TUI Integration

[OpenCode](https://opencode.ai) is a terminal-based AI assistant that supports custom OpenAI-compatible providers. This allows you to chat with your self-hosted Gemma 4 directly from a terminal TUI.

### Prerequisites
- Install Node.js 18+ and npm
- Install OpenCode: download from [opencode.ai/download](https://opencode.ai/download)

### Step 1: Configure Provider

Create/edit the config file:
- **Linux/macOS**: `~/.config/opencode/opencode.json`
- **Windows**: `C:\Users\<username>\.config\opencode\opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "hora-gemma/gemma4:e4b",
  "provider": {
    "hora-gemma": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Hora Gemma 4",
      "options": {
        "baseURL": "http://YOUR_VPS_IP:8000/v1",
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

> 💡 **Why high timeouts?** The first request triggers a cold model load (~50s-2min). Set `timeout: 600000` (10 min) and `chunkTimeout: 60000` (1 min) to avoid premature disconnects.

### Step 2: Configure Credentials

Create/edit the auth file:
- **Linux/macOS**: `~/.local/share/opencode/auth.json`
- **Windows**: `C:\Users\<username>\.local\share\opencode\auth.json`

```json
{
  "hora-gemma": {
    "type": "api",
    "key": "YOUR_API_KEY"
  }
}
```

### Step 3: Run!

```bash
# One-shot query:
opencode run "Tell me a fun space fact." --model hora-gemma/gemma4:e4b --pure --dangerously-skip-permissions

# Interactive chat session:
opencode run --model hora-gemma/gemma4:e4b --pure --dangerously-skip-permissions
```

---

## Bitwarden Secrets Vault Sync

This repository includes an automated utility to securely vault your sensitive files (`.env` and SSH key `test_key`) into a `"Hora"` folder in your Bitwarden Vault.

### Prerequisites
1. Install Bitwarden CLI: `npm install -g @bitwarden/cli`
2. Log in: `bw login`
3. Add your master password to `.env`:
   ```env
   BW_PASSWORD=your_bitwarden_master_password
   ```

### Run the Sync

```powershell
# Windows PowerShell:
.\deploy\sync_secrets.ps1

# Cross-platform Python:
python deploy/sync_secrets.py
```

### What It Does
1. Unlocks your Bitwarden vault using the `BW_PASSWORD` from `.env`
2. Finds or creates a folder named `"Hora"` in your vault
3. Creates/updates two Secure Notes:
   - `Hora Model Host - Environment Secrets (.env)` — your full `.env` contents
   - `Hora Model Host - SSH Private Key (test_key)` — your SSH private key
4. Prevents duplicates by updating existing items in-place

### Security Guarantees
| File | Contains | Git-tracked? |
|---|---|---|
| `.env` | API_KEY, BW_PASSWORD, all secrets | ❌ Gitignored |
| `test_key` / `test_key.pub` | SSH keypair | ❌ Gitignored |
| `performance_report.md` | Benchmark data | ❌ Gitignored |
| `.env.example` | Placeholder template only | ✅ Safe |

---

## Operations & Troubleshooting

### Monitoring

```bash
# Check gateway service status
systemctl status gateway

# Stream live logs
journalctl -u gateway -f -n 100

# Check Ollama health
curl http://localhost:11434/api/tags
```

### Restarting Services

```bash
# Restart gateway after code/config changes
systemctl restart gateway

# Restart Ollama
systemctl restart ollama
```

### API Key Rotation

1. Generate a new key: `python3 -c "import secrets; print(f'hora_live_{secrets.token_hex(16)}')"`
2. Update `/opt/hora-model-host/.env` on VPS
3. Update your local `.env`
4. Restart gateway: `systemctl restart gateway`
5. Update client configs (OpenCode auth.json, etc.)
6. Re-sync to Bitwarden: `python deploy/sync_secrets.py`

### Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| First request takes 1-2 min | Ollama loading model into RAM (cold start) | Wait; or set `OLLAMA_KEEP_ALIVE=-1` |
| `401 Unauthorized` | Missing or wrong Bearer token | Verify API_KEY in `.env` and client config |
| OpenCode hangs on connect | Missing public `/` or `/v1` endpoints | Ensure gateway has unauthenticated root routes |
| `502 Bad Gateway` | Ollama not running or crashed | `systemctl restart ollama` |
| `npm` hooks fail during install | `node` not on subprocess PATH | Add Node.js to PATH explicitly |

---

## Performance Benchmarks

| Metric | Value |
|---|---|
| **Hardware** | AMD EPYC CPU (12 Cores, 48GB RAM, No GPU) |
| **Model** | Gemma 4 E4B (4-bit quantized, 9.6 GB) |
| **Cold Start (TTFT)** | ~50 seconds – 2 minutes |
| **Active Generation** | 9.13 tokens/second |
| **Memory Usage** | ~34 MB (gateway) + ~9.6 GB (model in RAM) |
| **Gateway Overhead** | <1ms per request (pure async proxy) |

---

## Lessons Learned

### 🪤 The "Pre-flight Check" Trap
Many OpenAI-compatible SDKs (including `@ai-sdk/openai-compatible` used by OpenCode) send unauthenticated `GET /` or `GET /v1` requests before making actual API calls. If your gateway returns `401 Unauthorized` on these routes, clients will silently fail or hang. **Always expose public discovery endpoints.**

### ⏱️ CPU RAM Lifecycles & Keep-Alive
Ollama unloads models after 5 minutes of inactivity by default. For production use, configure permanent residency:
```bash
# Add to Ollama's systemd override
systemctl edit ollama
# Add under [Service]:
Environment="OLLAMA_KEEP_ALIVE=-1"
```

### 🔧 Environment Path Inheritance
When npm postinstall hooks run in subprocess environments, they often can't find `node` because the parent shell's PATH isn't inherited. Always construct explicit PATH strings when launching automated scripts.

### 🔐 Secrets Hygiene
Never commit `.env` files. Use `.env.example` as a public template, `.gitignore` to block secrets, and Bitwarden CLI to vault credentials for cross-machine recovery.

---

## Further Reading

- 📖 **[Wiki: Home](https://github.com/aarshps/hora-model-host/wiki)** — Project overview and navigation
- 📖 **[Wiki: Architecture](https://github.com/aarshps/hora-model-host/wiki/Architecture)** — System design deep-dive
- 📖 **[Wiki: API Reference](https://github.com/aarshps/hora-model-host/wiki/API-Reference)** — Complete endpoint documentation
- 📖 **[Wiki: Deployment Guide](https://github.com/aarshps/hora-model-host/wiki/Deployment-Guide)** — Full operational runbook
