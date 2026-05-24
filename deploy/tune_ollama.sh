#!/usr/bin/env bash
# =============================================================================
# tune_ollama.sh
# -----------------------------------------------------------------------------
# Applies a tuned systemd override for the Ollama daemon, optimized for
# CPU-only servers running a single primary model. Designed to be safe by
# default (prints the plan, requires --apply to write).
#
# Why this exists:
#   Out-of-the-box Ollama is conservative. The defaults assume mixed workloads
#   and short keep-alives, which produces cold-start stalls on every request.
#   For a self-hosted agent (OpenClaw, Hermes, OpenCode, your own client),
#   you almost always want:
#     - keep the primary model permanently resident
#     - quantize the KV cache so context is cheap
#     - use flash attention
#     - cap loaded models so you can't accidentally OOM the box
#
# Usage:
#   sudo deploy/tune_ollama.sh                 # dry-run, prints plan
#   sudo deploy/tune_ollama.sh --apply         # writes + restarts ollama
#   sudo deploy/tune_ollama.sh --keep-alive 5m --apply   # safer multi-model
#
# Flags:
#   --keep-alive <duration>   default: -1 (forever)
#   --max-loaded  <N>         default: 1
#   --num-parallel <N>        default: 1
#   --context     <N>         default: 8192
#   --threads     <N>         default: detected physical cores
#   --kv-cache    <type>      default: q4_0 (other: q8_0, f16)
#   --apply                   write override + restart ollama
#   --revert                  remove override + restart ollama
# =============================================================================
set -euo pipefail

KEEP_ALIVE="-1"
MAX_LOADED="1"
NUM_PARALLEL="1"
CONTEXT="8192"
KV_CACHE="q4_0"
THREADS=""
APPLY="false"
REVERT="false"

OVERRIDE_DIR="/etc/systemd/system/ollama.service.d"
OVERRIDE_FILE="$OVERRIDE_DIR/override.conf"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-alive)   KEEP_ALIVE="$2"; shift 2 ;;
    --max-loaded)   MAX_LOADED="$2"; shift 2 ;;
    --num-parallel) NUM_PARALLEL="$2"; shift 2 ;;
    --context)      CONTEXT="$2"; shift 2 ;;
    --threads)      THREADS="$2"; shift 2 ;;
    --kv-cache)     KV_CACHE="$2"; shift 2 ;;
    --apply)        APPLY="true"; shift ;;
    --revert)       REVERT="true"; shift ;;
    -h|--help)
      sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$THREADS" ]]; then
  THREADS="$(nproc --all 2>/dev/null || echo 4)"
fi

if [[ "$REVERT" == "true" ]]; then
  echo "[tune_ollama] Reverting: removing $OVERRIDE_FILE"
  if [[ "$APPLY" == "true" ]]; then
    rm -f "$OVERRIDE_FILE"
    systemctl daemon-reload
    systemctl restart ollama
    echo "[tune_ollama] Reverted to stock Ollama defaults."
  else
    echo "[tune_ollama] (dry-run) Pass --apply to actually remove."
  fi
  exit 0
fi

cat <<EOF
[tune_ollama] Planned configuration:
  Override file:       $OVERRIDE_FILE
  OLLAMA_KEEP_ALIVE        = $KEEP_ALIVE
  OLLAMA_MAX_LOADED_MODELS = $MAX_LOADED
  OLLAMA_NUM_PARALLEL      = $NUM_PARALLEL
  OLLAMA_CONTEXT_LENGTH    = $CONTEXT
  OLLAMA_NUM_THREAD        = $THREADS
  OLLAMA_KV_CACHE_TYPE     = $KV_CACHE
  OLLAMA_FLASH_ATTENTION   = 1
EOF

if [[ "$KEEP_ALIVE" == "-1" && "$MAX_LOADED" != "1" ]]; then
  echo
  echo "[tune_ollama] WARNING: keep-alive=-1 with max-loaded>1 can OOM the VPS"
  echo "[tune_ollama] if multiple large models get triggered. Consider --max-loaded 1."
fi

if [[ "$APPLY" != "true" ]]; then
  echo
  echo "[tune_ollama] (dry-run) Pass --apply to write override and restart ollama."
  exit 0
fi

mkdir -p "$OVERRIDE_DIR"
cat <<EOF > "$OVERRIDE_FILE"
[Service]
Environment="OLLAMA_KEEP_ALIVE=$KEEP_ALIVE"
Environment="OLLAMA_MAX_LOADED_MODELS=$MAX_LOADED"
Environment="OLLAMA_NUM_PARALLEL=$NUM_PARALLEL"
Environment="OLLAMA_CONTEXT_LENGTH=$CONTEXT"
Environment="OLLAMA_NUM_THREAD=$THREADS"
Environment="OLLAMA_KV_CACHE_TYPE=$KV_CACHE"
Environment="OLLAMA_FLASH_ATTENTION=1"
EOF

systemctl daemon-reload
systemctl restart ollama

echo "[tune_ollama] Override written and Ollama restarted."
echo "[tune_ollama] Verify with: systemctl show ollama -p Environment"
