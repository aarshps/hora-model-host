#!/usr/bin/env bash
# =============================================================================
# install_openclaw.sh — Install + wire up OpenClaw on the VPS.
# -----------------------------------------------------------------------------
# Reusable installer for the OpenClaw self-hosted agent. Designed for a
# fresh Ubuntu 24.04 box with Ollama already installed (run deploy/install.sh
# and deploy/tune_ollama.sh first).
#
# Required env (pass inline or export):
#   TELEGRAM_BOT_TOKEN   — from @BotFather
#   MODEL_ID             — Ollama tag, e.g. qwen2.5:7b-instruct
#
# Usage:
#   sudo MODEL_ID=qwen2.5:7b-instruct \
#        TELEGRAM_BOT_TOKEN=123:abc \
#        deploy/install_openclaw.sh
# =============================================================================
set -euo pipefail

: "${MODEL_ID:?Set MODEL_ID (e.g. qwen2.5:7b-instruct)}"
: "${TELEGRAM_BOT_TOKEN:?Set TELEGRAM_BOT_TOKEN from @BotFather}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE_DIR="$REPO_ROOT/deploy/templates"
OPENCLAW_HOME="/root/.openclaw"

echo "[install_openclaw] Installing OpenClaw CLI..."
if ! command -v openclaw &>/dev/null; then
  curl -fsSL https://openclaw.ai/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "[install_openclaw] Preparing workspace at $OPENCLAW_HOME"
mkdir -p "$OPENCLAW_HOME/workspace/scratch"
mkdir -p "$OPENCLAW_HOME/workspace/artifacts"
mkdir -p "$OPENCLAW_HOME/workspace/skills"

echo "[install_openclaw] Materializing config from template"
envsubst < "$TEMPLATE_DIR/openclaw.json" > "$OPENCLAW_HOME/openclaw.json"
cp "$TEMPLATE_DIR/IDENTITY.md" "$OPENCLAW_HOME/workspace/IDENTITY.md"
cp "$TEMPLATE_DIR/TOOLS.md"    "$OPENCLAW_HOME/workspace/TOOLS.md"
chmod 600 "$OPENCLAW_HOME/openclaw.json"

echo "[install_openclaw] Confirming Ollama has $MODEL_ID..."
if ! curl -fsS "http://127.0.0.1:11434/api/tags" | grep -q "\"$MODEL_ID\""; then
  echo "[install_openclaw]   not found — pulling now (may take several minutes)"
  ollama pull "$MODEL_ID"
fi

echo "[install_openclaw] Installing user-level daemon..."
openclaw onboard --install-daemon --non-interactive || true
openclaw gateway restart || openclaw gateway start

cat <<EOF

============================================================
OpenClaw installed.

Next:
  1. Open Telegram and DM your bot. Send /start.
  2. The bot will print a Pairing Code (e.g. ABCDEFGH).
  3. Approve on the VPS:
       openclaw pairing approve telegram <CODE>
  4. Tail logs:
       export XDG_RUNTIME_DIR=/run/user/0
       journalctl --user -u openclaw-gateway -f
============================================================
EOF
