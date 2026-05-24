# Hora Model Host

> A reusable, **model-agnostic** harness for hosting open-source LLMs on a
> CPU-only VPS — with a secure OpenAI-compatible gateway, perf-tuning
> scripts, and one-shot installers for the **OpenClaw** and **Hermes Agent**
> messaging agents (Telegram, Discord, Slack, WhatsApp…).
>
> Reference deployment: **"Con Taboclo"**, a personal Telegram agent
> running on a Contabo VPS. Fork the repo, swap the env values, and you
> have your own.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)]()
[![Ollama](https://img.shields.io/badge/Ollama-latest-orange.svg)]()

---

## What you get

| Layer | What it is | File |
|---|---|---|
| **Model serving** | FastAPI gateway in front of Ollama, Bearer-auth'd, streaming | `gateway/` |
| **Perf tuning** | One-shot script: KV-cache quantization, flash attention, keep-alive | `deploy/tune_ollama.sh` |
| **Benchmark** | Standardized t/s harness so you can compare models | `deploy/benchmark_model.py` |
| **OpenClaw install** | One-shot installer for the OpenClaw Telegram agent | `deploy/install_openclaw.sh` |
| **Hermes Agent install** | One-shot installer for Hermes Agent (with OpenClaw migration) | `deploy/install_hermes.sh` |
| **Agent templates** | Reusable `openclaw.json`, `hermes-config.yaml`, `IDENTITY.md`, `TOOLS.md` | `deploy/templates/` |
| **Secrets vaulting** | Sync `.env` + SSH keys to Bitwarden | `deploy/sync_secrets.py` |
| **Docs** | Full setup runbooks, decision matrices, perf math | [wiki](https://github.com/aarshps/hora-model-host/wiki) |

---

## Five-minute happy path

```bash
ssh -i test_key root@<VPS_IP>
git clone https://github.com/aarshps/hora-model-host /opt/hora-model-host
cd /opt/hora-model-host

# 1. Gateway + Ollama
bash deploy/install.sh

# 2. Apply the perf-tuning preset (one of the highest-impact knobs)
sudo deploy/tune_ollama.sh --apply

# 3. Pick + pull a fast model — see wiki/Choosing-a-Model for the matrix
ollama pull qwen2.5:7b-instruct
sed -i 's/^MODEL_ID=.*/MODEL_ID=qwen2.5:7b-instruct/' .env
systemctl restart gateway

# 4. Wire up Telegram — pick ONE:
#    OpenClaw (stable, since Nov 2025):
sudo MODEL_ID=qwen2.5:7b-instruct \
     TELEGRAM_BOT_TOKEN=<token-from-BotFather> \
     deploy/install_openclaw.sh

#    OR Hermes Agent (newer, self-improving, since Feb 2026):
sudo MODEL_ID=qwen2.5:7b-instruct \
     TELEGRAM_BOT_TOKEN=<token-from-BotFather> \
     deploy/install_hermes.sh

# 5. On Telegram: DM your bot, send /start, copy the pairing code,
#    then on the VPS:
openclaw pairing approve telegram <CODE>     # or: hermes pair approve telegram <CODE>
```

You now have a self-hosted personal AI agent reachable from your phone.

---

## Architecture (TL;DR)

```
[Telegram] [Discord] [SDKs] [curl] [OpenCode TUI]
     │         │       │      │         │
     ▼         ▼       ▼      ▼         ▼
  ┌─────────────────────────────────────┐
  │ Agent layer (OpenClaw / Hermes)     │  ← optional, swap freely
  └────────────────┬────────────────────┘
                   │ OpenAI-compatible HTTP + Bearer
  ┌────────────────▼────────────────────┐
  │ FastAPI gateway (this repo, :8000)  │
  └────────────────┬────────────────────┘
                   │ localhost:11434
  ┌────────────────▼────────────────────┐
  │ Ollama daemon (tuned)               │
  └────────────────┬────────────────────┘
                   │
              [Your model]
```

The harness deliberately separates **model serving** from **agent logic** so
each can be swapped independently. See [Architecture](https://github.com/aarshps/hora-model-host/wiki/Architecture).

---

## Repository layout

```
hora-model-host/
├── gateway/                     # FastAPI gateway (model-agnostic)
│   ├── main.py                  # auth, proxy, discovery endpoints
│   ├── config.py                # env loader (MODEL_ID, API_KEY, …)
│   └── requirements.txt
├── deploy/
│   ├── install.sh               # bootstrap Ollama + gateway + systemd
│   ├── gateway.service          # systemd unit for the gateway
│   ├── tune_ollama.sh           # ★ apply perf-tuning systemd override
│   ├── benchmark_model.py       # ★ standardized t/s benchmark
│   ├── install_openclaw.sh      # ★ Telegram agent installer (OpenClaw)
│   ├── install_hermes.sh        # ★ Telegram agent installer (Hermes Agent)
│   ├── setup_vps_models.py      # pull multiple models in one shot
│   ├── verify_new_models.py     # smoke-test installed models
│   ├── sync_secrets.py          # vault .env + SSH key to Bitwarden
│   ├── sync_secrets.ps1         # PowerShell wrapper for above
│   └── templates/
│       ├── openclaw.json        # ★ reusable OpenClaw config
│       ├── hermes-config.yaml   # ★ reusable Hermes Agent config
│       ├── IDENTITY.md          # ★ persona file for the agent
│       └── TOOLS.md             # ★ tool-use guidance for the agent
├── .env                         # 🔒 LOCAL ONLY — gitignored
├── .env.example                 # template (MODEL_ID, API_KEY, TELEGRAM_BOT_TOKEN, …)
├── agent_skills.md              # knowledge-transfer manual for AI agents
└── README.md
```

★ = new in v1.1 (the reusability + agent-layer overhaul).

---

## Environment variables

| Variable | Description | Example |
|---|---|---|
| `PORT` | Gateway listen port | `8000` |
| `OLLAMA_BASE_URL` | Internal Ollama endpoint | `http://localhost:11434` |
| `API_KEY` | Bearer token clients must send | `hora_live_8e94a7cb…` |
| `MODEL_ID` | Ollama tag to serve | `qwen2.5:7b-instruct` |
| `DEPLOYMENT_NAME` | Human label in discovery responses | `Con Taboclo VPS` |
| `BW_PASSWORD` | Bitwarden master password (only for sync_secrets) | — |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather (only for agent installers) | `123:abc…` |
| `GEMMA_MODEL` | **Deprecated** alias for `MODEL_ID`, still honored | — |

---

## Quick client examples

### cURL

```bash
curl -X POST http://<VPS_IP>:8000/v1/chat/completions \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:7b-instruct","messages":[{"role":"user","content":"Hello"}],"stream":false}'
```

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(api_key="<KEY>", base_url="http://<VPS_IP>:8000/v1")
stream = client.chat.completions.create(
    model="qwen2.5:7b-instruct",
    messages=[{"role": "user", "content": "Hi!"}],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

More clients (Node, OpenCode TUI, OpenClaw, Hermes) in the
[API Reference](https://github.com/aarshps/hora-model-host/wiki/API-Reference).

---

## Performance

| Metric | Value |
|---|---|
| **Hardware** | AMD EPYC, 12 cores, 48 GB RAM, no GPU (Contabo VPS XL) |
| **Gateway overhead** | <1 ms per request |
| **qwen2.5:7b-instruct Q4** (recommended) | 4–7 tokens/sec |
| **phi-4-mini Q4** (snappiest agentic option) | 6–10 tokens/sec |
| **qwen3.6:35b** (legacy — too big for CPU) | 1.19 tokens/sec |
| **Cold start** with `OLLAMA_KEEP_ALIVE=-1` | 0 s after first load |

If you want to go fast: read [Performance Tuning](https://github.com/aarshps/hora-model-host/wiki/Performance-Tuning).
There's a memory-bandwidth ceiling on CPU inference that no amount of
software trickery can dodge — the fix is **smaller weights**.

---

## Bitwarden secrets vault (optional)

```bash
npm install -g @bitwarden/cli
bw login
echo 'BW_PASSWORD=<master-password>' >> .env
python deploy/sync_secrets.py
```

Vaults your `.env` and `test_key` into a `Hora` folder in your Bitwarden
vault. Safe across machine wipes. Full details in
[Deployment Guide](https://github.com/aarshps/hora-model-host/wiki/Deployment-Guide#7-bitwarden-vault-sync).

---

## Choosing an agent layer

Two well-supported open-source options in 2026 — both MIT, both multi-channel,
both work with Ollama:

| | OpenClaw | Hermes Agent |
|---|---|---|
| Released | Nov 2025 (renamed from Clawdbot in Jan 2026) | Feb 2026 |
| Author | Peter Steinberger | Nous Research |
| Stars | 15K+ | Currently #1 trending in 2026 |
| Differentiator | Most-battle-tested, widest channel support | **Self-improving** — writes its own skills from experience |
| Migration helper | — | `hermes claw migrate` imports OpenClaw state |

Full side-by-side in [Choosing an Agent](https://github.com/aarshps/hora-model-host/wiki/Choosing-an-Agent).

---

## Lessons learned

### 🪤 The "pre-flight check" trap
OpenAI-compatible SDKs send unauthenticated `GET /` / `GET /v1` before any
real API call. If those return 401, clients silently hang. The gateway
deliberately exposes them as public — don't remove that.

### ⏱️ Cold-start latency is structural
On CPU, the first request loads weights from disk into RAM
(~50 s for 35B models). With `OLLAMA_KEEP_ALIVE=-1` and a single resident
model, you pay it once. With `KEEP_ALIVE=5m` you pay it after every quiet
period. `tune_ollama.sh --apply` defaults to the former.

### ⚡ The bottleneck is bandwidth, not the gateway
The gateway adds <1 ms. The model layer adds seconds. Don't optimize the
proxy — optimize the model choice.

### 🔐 Secrets hygiene
Never commit `.env`. `.env.example` is public, real `.env` is gitignored,
both vaulted in Bitwarden via `sync_secrets.py`. Same for `test_key`.

---

## Further reading

- 📖 [Wiki home](https://github.com/aarshps/hora-model-host/wiki) — full doc map
- 📖 [Architecture](https://github.com/aarshps/hora-model-host/wiki/Architecture)
- 📖 [Performance Tuning](https://github.com/aarshps/hora-model-host/wiki/Performance-Tuning)
- 📖 [Choosing a Model](https://github.com/aarshps/hora-model-host/wiki/Choosing-a-Model)
- 📖 [Choosing an Agent](https://github.com/aarshps/hora-model-host/wiki/Choosing-an-Agent)
- 📖 [OpenClaw Telegram Bot](https://github.com/aarshps/hora-model-host/wiki/OpenClaw-Telegram-Bot)
- 📖 [Hermes Agent Telegram Bot](https://github.com/aarshps/hora-model-host/wiki/Hermes-Agent-Telegram-Bot)
- 📖 [API Reference](https://github.com/aarshps/hora-model-host/wiki/API-Reference)
- 📖 [Deployment Guide](https://github.com/aarshps/hora-model-host/wiki/Deployment-Guide)
