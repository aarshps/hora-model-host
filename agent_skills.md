# Agent Skills & Knowledge Transfer Manual

> **Purpose**: This file is a structured memory artifact for AI agents (Antigravity, Gemini, etc.)
> taking over development of **Hora Model Host**. It captures all architectural decisions, runtime
> context, credentials locations, operational commands, and hard-won lessons from the deployment session.

---

## 1. System Overview

**Hora Model Host** is a deployment harness hosting a **Gemma 4** (`gemma4:e4b`) LLM on a CPU-only
Contabo VPS, exposed as an OpenAI-compatible public API behind a FastAPI security gateway.

### Network Topology
```
[External Client] --(Port 8000 / Bearer Auth)--> [FastAPI Reverse Proxy]
                                                        |
                                            (localhost:11434 / HTTP)
                                                        ↓
                                              [Ollama Daemon]
                                                        ↓
                                              [Gemma 4 model in RAM]
```

### Key Identifiers
| Resource          | Value                              |
|-------------------|------------------------------------|
| VPS IP            | `185.194.218.92`                   |
| VPS Provider      | Contabo                            |
| VPS OS            | Ubuntu 24.04 LTS (AMD EPYC)        |
| Gateway Port      | `8000` (public, UFW allowed)       |
| Ollama Port       | `11434` (localhost only, blocked)   |
| Model             | `gemma4:e4b` (4-bit, 9.6 GB)      |
| Gateway Install   | `/opt/hora-model-host/`            |
| Python Venv       | `/opt/hora-model-host/venv/`       |
| Systemd Service   | `gateway.service`                  |
| GitHub Repo       | `aarshps/hora-model-host`          |
| GitHub Wiki       | `aarshps/hora-model-host.wiki`     |

---

## 2. Security & Credentials

All secrets are **gitignored** and stored locally + vaulted in Bitwarden.

### Local Files (Never Committed)
| File              | Contains                                        |
|-------------------|-------------------------------------------------|
| `.env`            | PORT, OLLAMA_BASE_URL, API_KEY, GEMMA_MODEL, BW_PASSWORD |
| `test_key`        | SSH private key for VPS root access              |
| `test_key.pub`    | SSH public key                                   |
| `performance_report.md` | Local benchmark results                    |

### Bitwarden Vault
- **Folder**: `Hora` (ID: `2b3137dd-fe36-4e93-b2f8-b39c0157afa4`)
- **Items synced**:
  - `Hora Model Host - Environment Secrets (.env)` — full `.env` contents
  - `Hora Model Host - SSH Private Key (test_key)` — SSH private key
- **Sync script**: `deploy/sync_secrets.py` (reads `BW_PASSWORD` from `.env`)
- **Bitwarden CLI**: Installed globally via `npm install -g @bitwarden/cli`
- **Important**: `bw create/edit` commands require **base64-encoded** JSON on stdin

### .gitignore Rules
```
.env, *.env, .env.*, test_key*, performance_report.md
```

---

## 3. Dependencies

### VPS Server-Side
- Python 3.12+, Ollama (native), systemd, UFW, curl, git
- Python packages: `fastapi>=0.110.0`, `uvicorn>=0.28.0`, `httpx>=0.27.0`, `python-dotenv>=1.0.1`

### Local Developer Workstation
- Git (`C:\Program Files\Git\cmd\git.exe` — not on PATH in Antigravity shell)
- Python 3.12 (`C:\Users\Aarsh\AppData\Local\Programs\Python\Python312\python.exe`)
- Node.js 18+ (`C:\Program Files\nodejs\node.exe`)
- npm (`C:\Program Files\nodejs\npm.cmd`)
- Bitwarden CLI (`C:\Users\Aarsh\AppData\Roaming\npm\bw.cmd`)
- OpenCode TUI (installed at system level)

### Critical Path Note
The Antigravity shell does NOT have Git, Node.js, or npm on its PATH. You must use:
```powershell
$env:PATH = "C:\Program Files\nodejs;C:\Users\Aarsh\AppData\Roaming\npm;" + $env:PATH
& "C:\Program Files\Git\cmd\git.exe" <command>
```

---

## 4. Architecture Decisions

### Public Discovery Endpoints
The gateway exposes `GET /`, `GET /v1`, and `GET /health` **without authentication**.
This is critical because OpenAI-compatible clients (OpenCode, LangChain, ai-sdk) send
unauthenticated pre-flight pings before making API calls. If these return 401, clients
silently hang or fail.

### Streaming Proxy Design
The gateway uses `httpx.AsyncClient` with `stream=True` to pipe Ollama responses
chunk-by-chunk to the client. Headers like `content-length`, `transfer-encoding`, and
`connection` are stripped from the forwarded response to prevent HTTP framing conflicts.

### Systemd Service Configuration
```ini
[Service]
User=root
WorkingDirectory=/opt/hora-model-host
ExecStart=/opt/hora-model-host/venv/bin/uvicorn gateway.main:app --host 0.0.0.0 --port 8000
Restart=always
EnvironmentFile=/opt/hora-model-host/.env
```

### Ollama Keep-Alive
Default: 5 min inactivity → model unloads → next request cold-starts (~50s-2min).
Production fix: Set `OLLAMA_KEEP_ALIVE=-1` in systemd override to keep model in RAM.

---

## 5. Commands for Future Agents

### VPS Access
```bash
ssh -i test_key root@185.194.218.92
```

### Gateway Management
```bash
systemctl status gateway           # Check service health
systemctl restart gateway          # Restart after code changes
journalctl -u gateway -f -n 100    # Stream live logs
```

### Ollama Management
```bash
ollama list                        # List downloaded models
ollama pull gemma4:e4b             # Pull/update model
curl http://localhost:11434/v1/models  # Check models via API
```

### Remote Script Execution (from Windows)
The deployment uses Python scripts with `paramiko` for SSH/SFTP operations.
Pattern used throughout this session:
```python
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(r"c:\Users\Aarsh\Source\hora-model-host\test_key")
client.connect("185.194.218.92", username="root", pkey=key)
stdin, stdout, stderr = client.exec_command("your command here")
```

### Git Operations (Antigravity Shell)
```powershell
# Main repo
& "C:\Program Files\Git\cmd\git.exe" -C "c:\Users\Aarsh\Source\hora-model-host" add .
& "C:\Program Files\Git\cmd\git.exe" -C "c:\Users\Aarsh\Source\hora-model-host" commit -m "msg"
& "C:\Program Files\Git\cmd\git.exe" -C "c:\Users\Aarsh\Source\hora-model-host" push origin master

# Wiki repo
& "C:\Program Files\Git\cmd\git.exe" -C "c:\Users\Aarsh\Source\hora-model-host.wiki" add .
& "C:\Program Files\Git\cmd\git.exe" -C "c:\Users\Aarsh\Source\hora-model-host.wiki" commit -m "msg"
& "C:\Program Files\Git\cmd\git.exe" -C "c:\Users\Aarsh\Source\hora-model-host.wiki" push origin master
```

### Bitwarden Vault Sync
```powershell
$env:PATH = "C:\Program Files\nodejs;C:\Users\Aarsh\AppData\Roaming\npm;" + $env:PATH
& "C:\Users\Aarsh\AppData\Local\Programs\Python\Python312\python.exe" "c:\Users\Aarsh\Source\hora-model-host\deploy\sync_secrets.py"
```

---

## 6. API Endpoints Reference

| Method | Path                    | Auth Required | Purpose                          |
|--------|-------------------------|---------------|----------------------------------|
| GET    | `/`                     | No            | Root discovery (pre-flight)      |
| GET    | `/v1`                   | No            | API v1 discovery (pre-flight)    |
| GET    | `/health`               | No            | Health check (Ollama status)     |
| POST   | `/v1/chat/completions`  | Yes (Bearer)  | Chat completion (stream/non)     |
| *      | `/{path:path}`          | Yes (Bearer)  | Catch-all proxy to Ollama        |

### Test Commands
```bash
# Health (public)
curl http://185.194.218.92:8000/health

# Chat (authenticated, non-streaming)
curl -X POST http://185.194.218.92:8000/v1/chat/completions \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:e4b","messages":[{"role":"user","content":"Hi"}],"stream":false}'
```

---

## 7. OpenCode TUI Integration

### Config Files (Windows Paths)
- Provider: `C:\Users\Aarsh\.config\opencode\opencode.json`
- Auth: `C:\Users\Aarsh\.local\share\opencode\auth.json`

### Provider Configuration
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
      "models": { "gemma4:e4b": { "name": "Gemma 4 (4B)" } }
    }
  }
}
```

### Auth Configuration
```json
{ "hora-gemma": { "type": "api", "key": "<API_KEY>" } }
```

### Key Timeout Settings
- `timeout: 600000` (10 min) — covers cold start model load
- `chunkTimeout: 60000` (1 min) — covers slow CPU token generation

---

## 8. Performance Benchmarks

| Metric               | Value                                    |
|----------------------|------------------------------------------|
| Hardware             | AMD EPYC vCPU (6 cores), 16 GB RAM      |
| Model                | Gemma 4 E4B (4-bit quantized, 9.6 GB)   |
| Cold Start (TTFT)    | ~50 seconds – 2 minutes                 |
| Active Generation    | 9.13 tokens/second                       |
| Gateway Memory       | ~34 MB (peak 35 MB)                      |
| Gateway CPU          | ~3.7s per 20 min uptime window           |

---

## 9. Known Issues & Workarounds

1. **Windows Console Encoding**: Python emoji output fails on cp1252 codepage.
   Fix: Force UTF-8 via `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`

2. **npm Global Installs**: `bw` and `opencode` are in `C:\Users\Aarsh\AppData\Roaming\npm\`
   which is NOT on Antigravity's PATH. Always prepend it explicitly.

3. **Bitwarden CLI base64**: `bw create item` and `bw edit item` require base64-encoded JSON
   on stdin, not raw JSON. Use `base64.b64encode(json_str.encode()).decode()`.

4. **Git Not on PATH**: Use full path `C:\Program Files\Git\cmd\git.exe` in all git commands.

5. **GitHub CLI Warning**: `gh.exe auth git-credential` warnings appear during push but are
   harmless — git falls back to stored credentials and pushes succeed.

---

## 10. Optimization Recommendations

1. **Permanent Model Residency**: Set `OLLAMA_KEEP_ALIVE=-1` in Ollama systemd overrides
   to eliminate cold-start latency entirely.

2. **HTTPS/TLS**: Deploy a Caddy or Nginx reverse proxy with Let's Encrypt auto-SSL
   in front of port 8000 for production-grade encryption.

3. **Rate Limiting**: Add FastAPI middleware for per-IP rate limiting to prevent abuse.

4. **Monitoring**: Set up a lightweight health-check cron or uptime monitor (e.g., UptimeRobot)
   that pings `/health` every 5 minutes.

5. **Model Upgrades**: If VPS is upgraded with more RAM, consider larger models like
   `gemma4:e12b` or `gemma4:e27b` for higher quality responses.
