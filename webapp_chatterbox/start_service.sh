#!/bin/bash
# Systemd-compatible startup script for Chatterbox services
# Manages 3 Chatterbox TTS instances and Flask app

set -e

# Activate virtual environment
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"

cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox
source chatterbox_venv/bin/activate

echo "Starting Chatterbox TTS Services..."

# Start Chatterbox TTS services in background
python chatterbox_service.py --port 20182 --gpu 0 &
CHATTERBOX_0_PID=$!

python chatterbox_service.py --port 20183 --gpu 1 &
CHATTERBOX_1_PID=$!

python chatterbox_service.py --port 20184 --gpu 2 &
CHATTERBOX_2_PID=$!

# Wait for TTS services to initialize with health check
echo "Waiting for Chatterbox TTS services to be ready..."
max_retries=60 # 60 * 2s = 120s timeout
for i in $(seq 1 $max_retries); do
    if curl -s http://localhost:20182/health > /dev/null && \
       curl -s http://localhost:20183/health > /dev/null && \
       curl -s http://localhost:20184/health > /dev/null; then
        echo "✅ All Chatterbox TTS services are online!"
        break
    fi
    echo "   [$i/$max_retries] Waiting for services..."
    sleep 2
done

echo "Chatterbox TTS services started (PIDs: $CHATTERBOX_0_PID, $CHATTERBOX_1_PID, $CHATTERBOX_2_PID)"

# Start Flask app (this will run in foreground for systemd)
echo "Starting Flask app on port 5004..."
exec python app.py

# Cleanup function (called on exit)
cleanup() {
    echo "Stopping Chatterbox services..."
    kill $CHATTERBOX_0_PID $CHATTERBOX_1_PID $CHATTERBOX_2_PID 2>/dev/null || true
}

trap cleanup EXIT
