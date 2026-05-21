# Agent Skills & Knowledge Transfer Manual

Welcome, Agent! This file is a memory artifact designed to transfer context, architectural decisions, and runtime knowledge from the previous Antigravity deployment session to any future AI agent taking over the development of **Hora Model Host**.

---

## 🗺️ System Overview & Context

The **Hora Model Host** hosts a highly optimized **Gemma 4** (`gemma4:e4b`) LLM on a CPU-only Contabo VPS (`185.194.218.92`), securely exposed as a public API behind a FastAPI gatekeeper proxy.

### Network Topology:
```text
[External Client] --(Public Port 8000 / Bearer Auth)--> [FastAPI Reverse Proxy]
                                                               |
                                                   (Local Port 11434 / HTTP)
                                                               ↓
                                                   [Ollama Daemon (127.0.0.1)]
                                                               ↓
                                                    [Gemma 4 model in RAM]
```

---

## 🔒 Security Configuration & Credentials

All secrets are strictly segregated into local, gitignored files to prevent leaking to remote repositories.

### Files & Locations:
- **`c:\Users\Aarsh\Source\hora-model-host\.env`**: Contains sensitive environment variables:
  * `PORT=8000` (Gateway public port)
  * `OLLAMA_BASE_URL=http://localhost:11434` (Internal Ollama link)
  * `API_KEY=hora_live_8e94a7cb2c114f0c9780a1d3fbc9581f` (Bearer token)
  * `GEMMA_MODEL=gemma4:e4b`
- **`test_key` / `test_key.pub`**: SSH keypair used for VPS SFTP upload and command execution during bootstrapping.

### Gitignore Integrity:
The `.gitignore` explicitly prevents the following files from leaving the local machine:
```text
.env
*.env
test_key*
performance_report.md
```

---

## ⚡ Deployment & Verification Log

### Installation Path on VPS:
All gateway files reside under `/opt/hora-model-host/` on the remote server.

### Deployment Script (`deploy/install.sh`):
1. Installs Ollama natively on the Debian/Ubuntu host if not present.
2. Configures Ollama service to start automatically.
3. Pulls `gemma4:e4b` model (quantized 4B parameter model optimized for CPU).
4. Creates a Python 3.12 virtual environment at `/opt/hora-model-host/venv`.
5. Installs FastAPI, Uvicorn, and HTTPX dependencies.
6. Sets up `/etc/systemd/system/gateway.service` to daemonize the FastAPI gateway.
7. Enables and starts the `gateway` daemon.
8. Configures `ufw` to open port `8000` publicly while leaving Ollama port `11434` internal.

### Warmed-up Benchmarks (AMD EPYC CPU):
- **Time to First Token (TTFT)**: ~49.8 seconds (cold start model loading).
- **Active Generation Speed**: **9.13 tokens per second**.
- Full test trace and output samples can be read locally from [performance_report.md](performance_report.md).

---

## 🛠️ Commands for Future Agents

When resuming work, here are the exact commands you will need to monitor, manage, or edit this service:

### 1. Connecting to the VPS
```bash
ssh -i test_key root@185.194.218.92
```

### 2. Monitoring the Gateway logs
```bash
# Check service logs in real-time
journalctl -u gateway -f -n 100

# View service systemd state
systemctl status gateway
```

### 3. Restarting or Updating Code
If you upload updated files under `gateway/`:
```bash
# Restart gateway to load new Python code
systemctl restart gateway
```

### 4. Interacting with Ollama
```bash
# List downloaded models on the VPS
ollama list

# Pull a new model
ollama pull <model_name>
```

---

## 📈 Optimization Recommendations for Next Session
1. **Model Cache (Keep Alive)**: Ollama unloads models from memory after 5 minutes of inactivity. To prevent the ~50-second cold-start latency (TTFT), consider configuring Ollama's service environment with `OLLAMA_NUM_PARALLEL` and `OLLAMA_KEEP_ALIVE=-1` in the systemd overrides to keep the model permanently resident in RAM.
2. **Reverse Proxy TLS/HTTPS**: The current gateway runs over plain HTTP on port `8000`. For production security, place a Caddy or Nginx reverse proxy in front of port `8000` with automated Let's Encrypt SSL/TLS certificates.
