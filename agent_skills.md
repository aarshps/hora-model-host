# Agent Skills & Knowledge Transfer Manual

> **Purpose**: This file is a structured memory artifact for AI agents (Antigravity, Gemini, etc.)
> taking over development of **Hora Model Host**. It captures all architectural decisions, runtime
> context, credentials locations, operational commands, and hard-won lessons from the deployment session.

---

## 1. System Overview

**Hora Model Host** is a deployment harness hosting local LLMs (`qwen3.6:35b`, `gemma4:31b`, `gemma4:e4b`) on a CPU-only
Contabo VPS, exposed as an OpenAI-compatible public API behind a FastAPI security gateway.

### Network Topology
```
[External Client] --(Port 8000 / Bearer Auth)--> [FastAPI Reverse Proxy]
                                                        |
                                            (localhost:11434 / HTTP)
                                                        ↓
                                              [Ollama Daemon]
                                                        ↓
                                              [LLM Models in RAM]
```

### Key Identifiers
| Resource          | Value                              |
|-------------------|------------------------------------|
| VPS IP            | `185.194.218.92`                   |
| VPS Provider      | Contabo                            |
| VPS OS            | Ubuntu 24.04 LTS (AMD EPYC)        |
| Gateway Port      | `8000` (public, UFW allowed)       |
| Ollama Port       | `11434` (localhost only, blocked)   |
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

*(Note: SSH keys and profiling scratch files have been cleaned from the repo to ensure pristine tracking).*

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

### Ollama Memory & Concurrency Governance (CRITICAL)
- The VPS has exactly **48 GB RAM**.
- `gemma4:31b` takes ~27 GB, `qwen3.6:35b` takes ~23 GB. Combined they take 50 GB.
- **Deadlock Risk**: If `OLLAMA_KEEP_ALIVE=-1` (infinite keep-alive) is used, and a user tries to query both large models in parallel (or sequentially without eviction), the server will OOM or deadlock completely.
- **The Fix Applied**: `OLLAMA_KEEP_ALIVE=5m` is forced in the systemd `ollama.service` overrides. This means the model unloads after 5 minutes of inactivity, completely preventing out-of-memory crashes.
- `OLLAMA_NUM_PARALLEL=2` and `OLLAMA_MAX_LOADED_MODELS=3` are enabled, but they are intrinsically gated by the physical RAM limitations above.

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
ollama pull qwen3.6:35b            # Pull/update model
curl http://localhost:11434/v1/models  # Check models via API
journalctl -u ollama -n 100 --no-pager # Check for memory eviction loops
```

### Remote Script Execution (from Windows)
The deployment uses Python scripts with `paramiko` for SSH/SFTP operations.
```python
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# Agent NOTE: Key string may need to be pulled from Bitwarden into memory rather than disk for hygiene!
client.connect("185.194.218.92", username="root", password="<PW>")
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

---

## 6. API Endpoints Reference

| Method | Path                    | Auth Required | Purpose                          |
|--------|-------------------------|---------------|----------------------------------|
| GET    | `/`                     | No            | Root discovery (pre-flight)      |
| GET    | `/v1`                   | No            | API v1 discovery (pre-flight)    |
| GET    | `/health`               | No            | Health check (Ollama status)     |
| POST   | `/v1/chat/completions`  | Yes (Bearer)  | Chat completion (stream/non)     |
| *      | `/{path:path}`          | Yes (Bearer)  | Catch-all proxy to Ollama        |

---

## 7. OpenCode TUI Integration

### Config Files (Windows Paths)
- Provider: `C:\Users\Aarsh\.config\opencode\opencode.json`
- Auth: `C:\Users\Aarsh\.local\share\opencode\auth.json`

### Key Timeout Settings (CRITICAL)
- `timeout: 600000` (10 min) — covers extreme scenarios.
- `chunkTimeout: 120000` (2 min) — **MUST remain >= 120000**. Because the `qwen3.6:35b` model takes ~47-50 seconds to cold-start into memory from the NVMe disk, the default OpenCode timeout of 60 seconds (`60000`) will forcefully abort the connection right before the first token arrives. `120000` ensures OpenCode waits patiently for the model to "re-heat".

---

## 8. Performance Benchmarks

In-depth hardware profiling was performed natively on the CPU-only AMD EPYC VPS to determine true hardware capabilities without network latency:

| Model | Size | Load Time (Cold Start) | TTFT (Prompt Eval) | Generation Speed |
| :--- | :--- | :--- | :--- | :--- |
| **Gemma 4 (E4B)** | 9.6 GB | ~27.2 seconds | 2.28 seconds | **1.61 tokens/sec** |
| **Gemma 4 (31B)** | 26.6 GB | ~49.0 seconds | 14.37 seconds | **0.51 tokens/sec** |
| **Qwen 3.6 (35B-A3B)** | 23.0 GB | ~47.2 seconds | 5.01 seconds | **1.19 tokens/sec** |

### MoE Architecture Advantage
Qwen 3.6 35B generates tokens more than twice as fast as Gemma 4 31B (1.19 t/s vs 0.51 t/s) despite being a larger model. This is because Qwen is a **Mixture-of-Experts (MoE)** model (`35B-A3B`). It holds 35B parameters in RAM, but only activates ~3B parameters during inference, dramatically speeding up generation on CPUs!

---

## 9. Known Issues & Workarounds

1. **Windows Console Encoding**: Python emoji output fails on cp1252 codepage.
   Fix: Force UTF-8 via `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`

2. **Bitwarden CLI base64**: `bw create item` and `bw edit item` require base64-encoded JSON on stdin, not raw JSON. Use `base64.b64encode(json_str.encode()).decode()`.

3. **Git Not on PATH**: Use full path `C:\Program Files\Git\cmd\git.exe` in all git commands.

4. **"The operation timed out" in OpenCode**:
   If this occurs, it means the model was cold and took >60s to load. Check that `chunkTimeout` is set to `120000` in the local `opencode.json` config file!

---

## 10. Optimization Recommendations

1. **Keep-Alive Governance**: If the user insists on having zero cold-starts (`OLLAMA_KEEP_ALIVE=-1`), you MUST restrict `OLLAMA_MAX_LOADED_MODELS=1` to prevent the large models from competing for the 48GB physical RAM limit and bringing down the system.

2. **HTTPS/TLS**: Deploy a Caddy or Nginx reverse proxy with Let's Encrypt auto-SSL in front of port 8000 for production-grade encryption in the future.

3. **Rate Limiting**: Add FastAPI middleware for per-IP rate limiting to prevent abuse.

---

## 11. OpenClaw Telegram Bot Setup ("Con Taboclo")

OpenClaw is installed globally on the VPS as a self-hosted AI agent platform linking your local Ollama instance with your Telegram Account.

### Key Identifiers
| Parameter | Value |
|---|---|
| **Telegram Bot** | `@con_taboclou_bot` (http://t.me/con_taboclou_bot) |
| **Bot Token** | `8083785144:AAH4O8cbAmkFzxGtI2u4TzGyGO4wWtDn1hg` |
| **Agent ID** | `con-taboclo` |
| **Display Name** | `"Con Taboclo"` (configured via `IDENTITY.md`) |
| **Primary LLM** | `ollama/qwen3.6:35b` (local Ollama instance on `http://127.0.0.1:11434`) |
| **Workspace** | `/root/.openclaw/workspace` |
| **Config File** | `/root/.openclaw/openclaw.json` (JSON5) |
| **Systemd Service** | `openclaw-gateway.service` (root user-level systemd) |

### Service Management Commands
To manage OpenClaw, you must set `XDG_RUNTIME_DIR` in your SSH environment so systemd can locate the root user-level bus:
```bash
# Check service health
export XDG_RUNTIME_DIR=/run/user/0 && systemctl --user status openclaw-gateway

# Restart service (required after any manual openclaw.json edits)
export XDG_RUNTIME_DIR=/run/user/0 && systemctl --user restart openclaw-gateway

# View live trailing logs
export XDG_RUNTIME_DIR=/run/user/0 && journalctl --user -u openclaw-gateway -f -n 50 --no-pager
```

### DM Pairing & Account Access (CRITICAL)
For security, OpenClaw operates on a least-privilege model. You must authorize your personal Telegram account to interact with the bot:
1. Message `@con_taboclou_bot` on Telegram and send `/start`.
2. The bot will print a **Pairing Code** (e.g. `ABCDEFGH`) in its logs or in the chat.
3. Approve the pairing request via SSH to link your account:
   ```bash
   openclaw pairing approve telegram <CODE>
   ```
4. Once approved, you will have exclusive tool-enabled control of your agent!

