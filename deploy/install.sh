#!/bin/bash
# ==============================================================================
# Hora Model Host Deployment & Setup Script
# Works on Ubuntu 24.04 LTS (AMD EPYC CPU, 48GB RAM)
# ==============================================================================
set -e

# Configuration (overridable via env vars)
GATEWAY_DIR="/opt/hora-model-host"
GEMMA_MODEL="${GEMMA_MODEL:-gemma4:e4b}"
PORT="${PORT:-8000}"
API_KEY="${API_KEY:-}"

echo "===================================================================="
echo "Starting Hora Model Host Setup on VPS"
echo "===================================================================="

# 1. System Updates & Essential Packages
echo "1. Installing system dependencies..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip curl git systemd

# 2. Check and Install Ollama
echo "2. Checking for Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "Ollama is not installed. Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

# Ensure Ollama service is running
echo "Ensuring Ollama service is active..."
systemctl daemon-reload
systemctl enable ollama
systemctl restart ollama
sleep 5

# 3. Pull Gemma 4 model
echo "3. Pulling Gemma 4 model (${GEMMA_MODEL}). This might take a few minutes..."
ollama pull "$GEMMA_MODEL"
echo "Model pulled successfully."

# 4. Set up directories
echo "4. Organizing gateway files..."
mkdir -p "$GATEWAY_DIR"
mkdir -p "$GATEWAY_DIR/gateway"
# Files are already placed by SFTP deployment tool


# 5. Create Python Virtual Environment & Install requirements
echo "5. Setting up Python virtual environment..."
python3 -m venv "$GATEWAY_DIR/venv"
"$GATEWAY_DIR/venv/bin/pip" install --upgrade pip
"$GATEWAY_DIR/venv/bin/pip" install -r "$GATEWAY_DIR/gateway/requirements.txt"

# 6. Configure environment secrets
echo "6. Writing environment configuration..."
cat << EOF > "$GATEWAY_DIR/.env"
PORT=$PORT
OLLAMA_BASE_URL=http://localhost:11434
API_KEY=$API_KEY
GEMMA_MODEL=$GEMMA_MODEL
EOF
chmod 600 "$GATEWAY_DIR/.env"

# 7. Setup Systemd Service
echo "7. Setting up systemd gateway service..."
cp deploy/gateway.service /etc/systemd/system/gateway.service
systemctl daemon-reload
systemctl enable gateway
systemctl restart gateway

echo "===================================================================="
echo "Deployment Complete!"
echo "Gateway is running on port $PORT"
echo "Model configured: $GEMMA_MODEL"
echo "===================================================================="
systemctl status gateway --no-pager | head -n 15
