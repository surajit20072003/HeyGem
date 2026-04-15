#!/bin/bash
###############################################################################
# webapp_chatterbox — One-Click Installation Script
#
# Usage (after git clone):
#   cd HeyGem/webapp_chatterbox
#   bash install.sh
#
# Optional env vars you can pre-set:
#   SARVAM_API_KEY=your_key        (Indian language TTS)
#   HUGGING_FACE_HUB_TOKEN=hf_xxx  (Chatterbox model download)
#   HEYGEM_GPU_COUNT=3             (override auto-detected GPU count)
#   HEYGEM_DATA_DIR=/custom/path   (where GPU data dirs are created)
###############################################################################
set -e

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}ℹ  $*${NC}"; }
ok()      { echo -e "${GREEN}✅ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $*${NC}"; }
die()     { echo -e "${RED}❌ $*${NC}"; exit 1; }
section() { echo -e "\n${BOLD}${CYAN}══  $*  ══${NC}\n"; }

# ── Resolve paths relative to this script ────────────────────────────────────
WEBAPP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${HEYGEM_DATA_DIR:-/home/$(whoami)/heygem_data}"
PYTHON_VERSION="3.11.0"
VENV="$WEBAPP_DIR/chatterbox_venv"
COMPOSE_FILE="$WEBAPP_DIR/docker-compose.yml"
CURRENT_USER="$(whoami)"
PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"

section "HeyGem webapp_chatterbox Installer"
echo "  Dir  : $WEBAPP_DIR"
echo "  Data : $DATA_DIR"
echo "  User : $CURRENT_USER"
echo ""

[ "$EUID" -eq 0 ] && die "Do NOT run as root. Run as a normal user with sudo access."
[ ! -f "$WEBAPP_DIR/app.py" ] && die "app.py not found. Run this script from inside webapp_chatterbox/."

# ── Step 1: GPU ───────────────────────────────────────────────────────────────
section "Step 1 — GPU Detection"
command -v nvidia-smi &>/dev/null || die "nvidia-smi not found. Install NVIDIA drivers first."
GPU_COUNT="${HEYGEM_GPU_COUNT:-$(nvidia-smi --list-gpus | wc -l)}"
ok "Found $GPU_COUNT GPU(s)"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader 2>/dev/null | \
    while IFS= read -r line; do echo "   GPU $line"; done

if [ "$GPU_COUNT" -lt 3 ]; then
    warn "Recommended: 3 GPUs. Found $GPU_COUNT — TTS will share GPU(s)."
    read -rp "Continue with $GPU_COUNT GPU(s)? [y/N] " _c
    [[ ! "$_c" =~ ^[Yy]$ ]] && { info "Aborted."; exit 0; }
fi

# ── Step 2: System deps ───────────────────────────────────────────────────────
section "Step 2 — System Packages"
info "Installing ffmpeg, build-essential, netcat, etc..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    ffmpeg git curl wget \
    python3-pip python3-venv \
    build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libncursesw5-dev \
    xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    netcat-openbsd jq
ok "System packages ready"

# ── Step 3: Docker ────────────────────────────────────────────────────────────
section "Step 3 — Docker"
if ! command -v docker &>/dev/null; then
    warn "Docker not found — installing..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sed -i 's/docker-model-plugin//g' /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    sudo usermod -aG docker "$CURRENT_USER"
    ok "Docker installed. Log out and back in, then re-run this script."
    exit 0
fi
ok "Docker $(docker --version | cut -d' ' -f3)"

if ! groups | grep -q docker; then
    sudo usermod -aG docker "$CURRENT_USER"
    warn "Added to docker group. Log out/in and re-run this script."
    exit 0
fi

# ── Step 4: NVIDIA Container Toolkit ─────────────────────────────────────────
section "Step 4 — NVIDIA Container Toolkit"
if ! docker info 2>/dev/null | grep -q nvidia; then
    info "Installing nvidia-container-toolkit..."
    distribution=$(. /etc/os-release; echo "$ID$VERSION_ID")
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        sudo gpg --dearmor -o /usr/share/keyrings/nvidia-ct-keyring.gpg
    curl -sL "https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list" | \
        sed 's|deb https://|deb [signed-by=/usr/share/keyrings/nvidia-ct-keyring.gpg] https://|g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-ct.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
    ok "NVIDIA Container Toolkit installed"
else
    ok "NVIDIA Container Toolkit already configured"
fi

# ── Step 5: pyenv + Python 3.11 ──────────────────────────────────────────────
section "Step 5 — Python $PYTHON_VERSION (pyenv)"
export PYENV_ROOT PATH="$PYENV_ROOT/bin:$PATH"

if [ ! -d "$PYENV_ROOT" ]; then
    info "Installing pyenv..."
    curl https://pyenv.run | bash
    {
        echo 'export PYENV_ROOT="$HOME/.pyenv"'
        echo 'export PATH="$PYENV_ROOT/bin:$PATH"'
        echo 'eval "$(pyenv init - bash)"'
    } >> ~/.bashrc
fi
eval "$(pyenv init - bash)"

pyenv versions 2>/dev/null | grep -q "$PYTHON_VERSION" || {
    info "Installing Python $PYTHON_VERSION (takes ~5 min)..."
    pyenv install "$PYTHON_VERSION"
}
cd "$WEBAPP_DIR"
pyenv local "$PYTHON_VERSION"
ok "Python $(python --version)"

# ── API Keys (needed for model downloads in Steps 6b & 6c) ───────────────────
section "API Keys"
echo "  • SARVAM_API_KEY         — Indian language TTS (Kannada, Hindi, Tamil…)"
echo "  • HUGGING_FACE_HUB_TOKEN — Required to download Chatterbox & IndicTrans2 weights"
echo ""
if [ -z "${SARVAM_API_KEY:-}" ]; then
    read -rp "Enter SARVAM_API_KEY          (Enter to skip): " SARVAM_API_KEY
fi
if [ -z "${HUGGING_FACE_HUB_TOKEN:-}" ]; then
    read -rp "Enter HUGGING_FACE_HUB_TOKEN  (Enter to skip): " HUGGING_FACE_HUB_TOKEN
fi
SARVAM_API_KEY="${SARVAM_API_KEY:-}"
HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-}"
[ -n "$HUGGING_FACE_HUB_TOKEN" ] && export HUGGING_FACE_HUB_TOKEN

# ── Step 6: Virtual environment + packages ────────────────────────────────────
section "Step 6 — Python Packages"
if [ ! -d "$VENV" ]; then
    info "Creating virtual environment..."
    python -m venv "$VENV"
fi
source "$VENV/bin/activate"

info "Installing uv (fast installer)..."
pip install -q --upgrade pip uv

info "Installing requirements.txt (~10-20 min on first run)..."
uv pip install -r "$WEBAPP_DIR/requirements.txt"
ok "Python packages installed"

# ── Step 6b: IndicTrans2 model binary download ────────────────────────────────
section "Step 6b — IndicTrans2 Model (2.1 GB)"
# The ct2_fp16_model/model.bin is NOT in git (too large). Download from HuggingFace.
INDIC_MODEL_DIR="$WEBAPP_DIR/../models/IndicTrans2/en-indic-exp/en-indic-preprint/ct2_fp16_model"
INDIC_MODEL_DIR="$(realpath "$INDIC_MODEL_DIR" 2>/dev/null || echo "$INDIC_MODEL_DIR")"
INDIC_MODEL_BIN="$INDIC_MODEL_DIR/model.bin"

if [ -f "$INDIC_MODEL_BIN" ]; then
    ok "IndicTrans2 model.bin already exists ($(du -sh "$INDIC_MODEL_BIN" | cut -f1))"
else
    warn "IndicTrans2 model.bin not found — downloading from HuggingFace..."
    mkdir -p "$INDIC_MODEL_DIR"

    # Also create needed vocab files if missing
    if [ ! -f "$INDIC_MODEL_DIR/config.json" ]; then
        HF_REPO="ai4bharat/indictrans2-en-indic-1B"
        HF_BASE="https://huggingface.co/$HF_REPO/resolve/main"

        info "Downloading config.json ..."
        if [ -n "$HUGGING_FACE_HUB_TOKEN" ]; then
            curl -sL -H "Authorization: Bearer $HUGGING_FACE_HUB_TOKEN" \
                "$HF_BASE/ct2_fp16_model/config.json" -o "$INDIC_MODEL_DIR/config.json"
        else
            curl -sL "$HF_BASE/ct2_fp16_model/config.json" -o "$INDIC_MODEL_DIR/config.json"
        fi
    fi

    info "Downloading model.bin (~2.1 GB, this will take a few minutes)..."
    if [ -n "$HUGGING_FACE_HUB_TOKEN" ]; then
        curl -L --progress-bar \
            -H "Authorization: Bearer $HUGGING_FACE_HUB_TOKEN" \
            "https://huggingface.co/ai4bharat/indictrans2-en-indic-1B/resolve/main/ct2_fp16_model/model.bin" \
            -o "$INDIC_MODEL_BIN"
    else
        curl -L --progress-bar \
            "https://huggingface.co/ai4bharat/indictrans2-en-indic-1B/resolve/main/ct2_fp16_model/model.bin" \
            -o "$INDIC_MODEL_BIN"
    fi

    if [ -f "$INDIC_MODEL_BIN" ] && [ "$(stat -c%s "$INDIC_MODEL_BIN" 2>/dev/null || echo 0)" -gt 100000000 ]; then
        ok "IndicTrans2 model.bin downloaded ($(du -sh "$INDIC_MODEL_BIN" | cut -f1))"
    else
        warn "IndicTrans2 download may have failed or is incomplete."
        warn "Indian language TTS will NOT work until model.bin is present at:"
        echo "  $INDIC_MODEL_BIN"
        warn "You can retry: huggingface-cli download ai4bharat/indictrans2-en-indic-1B ct2_fp16_model/model.bin --local-dir \$(dirname \"$INDIC_MODEL_DIR\")"
    fi
fi

# ── Step 6c: Chatterbox TTS model pre-warm ────────────────────────────────────
section "Step 6c — Chatterbox TTS Model Pre-download"
info "Pre-downloading Chatterbox-Turbo weights from HuggingFace..."
info "(Resemble AI / chatterbox-turbo — requires HUGGING_FACE_HUB_TOKEN)"

if [ -n "$HUGGING_FACE_HUB_TOKEN" ]; then
    # Use the venv Python to trigger model download (lazy loading on import)
    "$VENV/bin/python" - <<'PYEOF'
import os, sys
try:
    from huggingface_hub import snapshot_download
    # Download Chatterbox-Turbo assets to local cache
    print("  Pulling ResembleAI/chatterbox weights...")
    snapshot_download(
        repo_id="ResembleAI/chatterbox",
        ignore_patterns=["*.md", "*.txt"],
    )
    print("  ✅ Chatterbox weights cached")
except Exception as e:
    print(f"  ⚠  Could not pre-cache Chatterbox weights: {e}")
    print("     Weights will download on first TTS request instead.")
PYEOF
    ok "Chatterbox model pre-download complete"
else
    warn "HUGGING_FACE_HUB_TOKEN not set — Chatterbox weights will download on first request."
    warn "Set the token to speed up first startup: export HUGGING_FACE_HUB_TOKEN=hf_xxx"
fi

# ── Step 7: Directories ───────────────────────────────────────────────────────
section "Step 7 — Directories"
sudo mkdir -p "$DATA_DIR/gpu0" "$DATA_DIR/gpu1" "$DATA_DIR/gpu2"
sudo chown -R "$CURRENT_USER:$CURRENT_USER" "$DATA_DIR"
mkdir -p "$WEBAPP_DIR/"{uploads,outputs,temp}
mkdir -p "$WEBAPP_DIR/library/"{videos,audios}
ok "Directories ready"

# ── Step 8: Patch docker-compose & pull image ─────────────────────────────────
section "Step 8 — HeyGem Docker Containers (Face Sync)"
# Patch volume paths if they still point to old server path
if ! grep -q "$DATA_DIR" "$COMPOSE_FILE" 2>/dev/null; then
    info "Patching docker-compose.yml → $DATA_DIR ..."
    sed -i "s|/home/administrator/heygem_data|$DATA_DIR|g" "$COMPOSE_FILE"
fi
info "Pulling guiji2025/heygem.ai (~5 GB, may take a while)..."
sudo docker pull guiji2025/heygem.ai

info "Starting containers..."
if command -v docker-compose &>/dev/null; then
    sudo docker-compose -f "$COMPOSE_FILE" up -d
else
    sudo docker compose -f "$COMPOSE_FILE" up -d
fi
ok "HeyGem containers started (ports 8390, 8391, 8392)"

# ── Step 9: start_service.sh — patch hardcoded path ─────────────────────────
section "Step 9 — start_service.sh Path Patch"
OLD_PATH="/nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox"
if grep -q "$OLD_PATH" "$WEBAPP_DIR/start_service.sh" && [ "$WEBAPP_DIR" != "$OLD_PATH" ]; then
    sed -i "s|cd $OLD_PATH|cd $WEBAPP_DIR|g" "$WEBAPP_DIR/start_service.sh"
    ok "start_service.sh patched → $WEBAPP_DIR"
else
    ok "start_service.sh path already correct"
fi
chmod +x "$WEBAPP_DIR/start_service.sh"
[ -f "$WEBAPP_DIR/restart_all.sh" ] && chmod +x "$WEBAPP_DIR/restart_all.sh"

# ── Step 10: Systemd services ────────────────────────────────────────────────
section "Step 10 — Systemd Services"

# Containers service
sudo tee /etc/systemd/system/heygem-chatterbox-containers.service > /dev/null <<EOF
[Unit]
Description=HeyGem Chatterbox GPU Docker Containers
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
WorkingDirectory=$WEBAPP_DIR
ExecStart=/usr/bin/docker compose -f $COMPOSE_FILE up -d
ExecStop=/usr/bin/docker compose -f $COMPOSE_FILE down
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Main service
sudo tee /etc/systemd/system/heygem-chatterbox.service > /dev/null <<EOF
[Unit]
Description=HeyGem Chatterbox TTS Video Generation Service
After=network-online.target heygem-chatterbox-containers.service
Wants=network-online.target
Requires=heygem-chatterbox-containers.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$WEBAPP_DIR
ExecStart=$WEBAPP_DIR/start_service.sh
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=PYENV_ROOT=$PYENV_ROOT
Environment=PATH=$PYENV_ROOT/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=SARVAM_API_KEY=$SARVAM_API_KEY
Environment=HUGGING_FACE_HUB_TOKEN=$HUGGING_FACE_HUB_TOKEN
StandardOutput=journal
StandardError=journal
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable heygem-chatterbox-containers heygem-chatterbox
ok "Systemd services installed and enabled"

# ── Step 12: Default media files check ───────────────────────────────────────
section "Step 12 — Default Media Files"
if [ -f "$WEBAPP_DIR/default.mp4" ]; then
    ok "default.mp4 found ($(du -sh "$WEBAPP_DIR/default.mp4" | cut -f1))"
else
    warn "default.mp4 NOT found!"
    echo "  → Place avatar video at: $WEBAPP_DIR/default.mp4"
    echo "  → Min: 720×1280 portrait MP4 with a talking person"
fi

if [ -f "$WEBAPP_DIR/reference_audio.wav" ]; then
    ok "reference_audio.wav found"
else
    warn "reference_audio.wav NOT found!"
    echo "  → Place voice clone reference at: $WEBAPP_DIR/reference_audio.wav"
fi

# ── Step 13: Start & health-check ────────────────────────────────────────────
section "Step 13 — Start Services"
read -rp "Start all services now? [Y/n] " _start
if [[ -z "$_start" || "$_start" =~ ^[Yy]$ ]]; then
    info "Starting GPU containers..."
    sudo systemctl start heygem-chatterbox-containers
    info "Waiting 20s for containers..."
    sleep 20

    info "Starting main service..."
    sudo systemctl start heygem-chatterbox
    info "Waiting 60s for TTS services to warm up..."
    sleep 60

    echo ""
    info "Health checks:"
    for port in 8390 8391 8392; do
        if curl -sf "http://localhost:$port" &>/dev/null; then
            ok "Container port $port responding"
        else
            warn "Container port $port: not yet ready (may still load)"
        fi
    done
    for port in 20182 20183 20184; do
        if curl -sf "http://localhost:$port/health" &>/dev/null; then
            ok "TTS port $port healthy"
        else
            warn "TTS port $port: loads on first request (lazy mode)"
        fi
    done
    if curl -sf "http://localhost:5004/api/info" &>/dev/null; then
        ok "Flask API on port 5004 responding"
    else
        warn "Flask API not yet up — tail logs: journalctl -u heygem-chatterbox -f"
    fi
else
    echo ""
    info "Start manually:"
    echo "  sudo systemctl start heygem-chatterbox-containers"
    echo "  sudo systemctl start heygem-chatterbox"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
cat <<EOF

$(echo -e "${BOLD}${GREEN}")
════════════════════════════════════════════════
  ✅ webapp_chatterbox Installation Complete!
════════════════════════════════════════════════
$(echo -e "${NC}")
  Install : $WEBAPP_DIR
  API     : http://localhost:5004
  TTS     : ports 20182, 20183, 20184
  Docker  : ports 8390, 8391, 8392

  Commands:
    sudo systemctl status heygem-chatterbox
    sudo journalctl -u heygem-chatterbox -f
    $WEBAPP_DIR/restart_all.sh

  API test:
    curl http://localhost:5004/api/info

  Docs: $WEBAPP_DIR/README.md
EOF
