"""Hora Model Host — Gateway Configuration.

Loads runtime config from a local `.env` file. The harness is model-agnostic:
configure `MODEL_ID` to whatever Ollama model tag you've pulled (e.g.
`qwen2.5:7b-instruct`, `phi-4-mini`, `gemma4:e4b`, `llama3.2:3b`).

The legacy `GEMMA_MODEL` variable is still honored as a fallback so existing
deployments keep working without an .env rewrite.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from root or local directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()

# App settings
PORT = int(os.getenv("PORT", 8000))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
API_KEY = os.getenv("API_KEY")

# Primary model identifier. `MODEL_ID` is the canonical name going forward;
# `GEMMA_MODEL` is kept as a backward-compatible alias for older deployments.
MODEL_ID = os.getenv("MODEL_ID") or os.getenv("GEMMA_MODEL", "qwen2.5:7b-instruct")

# Backward-compatible export — anything that still imports GEMMA_MODEL keeps working.
GEMMA_MODEL = MODEL_ID

# Optional human-friendly name for the deployment (shown in `/` and `/health`).
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "Hora Model Host")

if not API_KEY:
    # Raise warning or generate a fallback only for development
    print("WARNING: API_KEY is not set. The gateway will be unprotected!")
