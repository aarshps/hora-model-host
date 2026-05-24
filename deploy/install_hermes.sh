#!/usr/bin/env bash
# =============================================================================
# install_hermes.sh — Install Hermes Agent (Nous Research) on the VPS,
# optionally migrating from an existing OpenClaw install.
# -----------------------------------------------------------------------------
# Hermes Agent is OpenClaw's main 2026 alternative — same multi-channel model,
# plus a built-in self-improving skills loop. It supports one-shot migration
# from OpenClaw (`hermes claw migrate`).
#
# Required env:
#   TELEGRAM_BOT_TOKEN
#   MODEL_ID                 (e.g. qwen2.5:7b-instruct)
#
# Optional:
#   MIGRATE_FROM_OPENCLAW=1  (run `hermes claw migrate` after install)
#
# Usage:
#   sudo MODEL_ID=qwen2.5:7b-instruct \
#        TELEGRAM_BOT_TOKEN=123:abc \
#        MIGRATE_FROM_OPENCLAW=1 \
#        deploy/install_hermes.sh
# =============================================================================
set -euo pipefail

: "${MODEL_ID:?Set MODEL_ID (e.g. qwen2.5:7b-instruct)}"
: "${TELEGRAM_BOT_TOKEN:?Set TELEGRAM_BOT_TOKEN from @BotFather}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE_DIR="$REPO_ROOT/deploy/templates"
HERMES_HOME="/root/.hermes"

echo "[install_hermes] Installing Hermes Agent..."
if ! command -v hermes &>/dev/null; then
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
  # shellcheck disable=SC1090
  source "$HOME/.bashrc" 2>/dev/null || true
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "[install_hermes] Preparing workspace at $HERMES_HOME"
mkdir -p "$HERMES_HOME/workspace"
cp "$TEMPLATE_DIR/IDENTITY.md" "$HERMES_HOME/IDENTITY.md"

echo "[install_hermes] Writing config"
envsubst < "$TEMPLATE_DIR/hermes-config.yaml" > "$HERMES_HOME/config.yaml"
chmod 600 "$HERMES_HOME/config.yaml"

echo "[install_hermes] Confirming Ollama has $MODEL_ID..."
if ! curl -fsS "http://127.0.0.1:11434/api/tags" | grep -q "\"$MODEL_ID\""; then
  echo "[install_hermes]   not found — pulling now"
  ollama pull "$MODEL_ID"
fi

if [[ "${MIGRATE_FROM_OPENCLAW:-0}" == "1" ]]; then
  echo "[install_hermes] Migrating from existing OpenClaw install..."
  hermes claw migrate --overwrite || echo "[install_hermes] migrate failed (continuing)"
fi

echo "[install_hermes] Starting gateway"
hermes gateway start || hermes gateway restart

cat <<EOF

============================================================
Hermes Agent installed.

Next:
  1. DM your Telegram bot, send /start.
  2. Hermes prints a pairing handshake — approve in chat or via:
       hermes pair approve telegram <CODE>
  3. Tail logs:
       journalctl --user -u hermes-gateway -f --no-pager

To roll back to OpenClaw:
  systemctl --user stop hermes-gateway
  systemctl --user start openclaw-gateway
============================================================
EOF
