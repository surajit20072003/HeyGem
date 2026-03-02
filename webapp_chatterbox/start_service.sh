#!/bin/bash
# Systemd-compatible startup script for Chatterbox services
# Manages 3 Chatterbox TTS instances and Flask app

set -e

# Cleanup function
cleanup() {
    echo "🛑 Stopping Chatterbox services..."
    pkill -P $$ 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT EXIT

# Activate virtual environment
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"

cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox
source chatterbox_venv/bin/activate

echo "=================================================="
echo "🚀 HeyGem Chatterbox Service Startup"
echo "=================================================="

# Step 1: Verify GPU containers are healthy
echo ""
echo "1️⃣ Checking GPU Containers..."
for port in 8390 8391 8392; do
    # Simple port check - just see if container is listening
   if ! nc -z localhost $port 2>/dev/null && ! timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null; then
        echo "   ❌ GPU container on port $port not responding!"
        echo "   💡 Hint: Run 'sudo systemctl start heygem-chatterbox-containers'"
        exit 1
    fi
    echo "   ✅ GPU container on port $port is reachable"
done

# Step 2: Clean up any existing TTS processes
echo ""
echo "2️⃣ Cleaning up existing processes..."
pkill -f "chatterbox_service.py" 2>/dev/null && echo "   🧹 Killed existing TTS processes" || echo "   ✅ No existing processes found"
sleep 2

# Step 3: Start Chatterbox TTS services
echo ""
echo "3️⃣ Starting Chatterbox TTS Services..."

python chatterbox_service.py --port 20182 --gpu 0 >> chatterbox_gpu0.log 2>&1 &
CHATTERBOX_0_PID=$!
echo "   🎤 Started TTS GPU 0 (PID: $CHATTERBOX_0_PID, Port: 20182)"

python chatterbox_service.py --port 20183 --gpu 1 >> chatterbox_gpu1.log 2>&1 &
CHATTERBOX_1_PID=$!
echo "   🎤 Started TTS GPU 1 (PID: $CHATTERBOX_1_PID, Port: 20183)"

python chatterbox_service.py --port 20184 --gpu 2 >> chatterbox_gpu2.log 2>&1 &
CHATTERBOX_2_PID=$!
echo "   🎤 Started TTS GPU 2 (PID: $CHATTERBOX_2_PID, Port: 20184)"

# Step 4: Wait for TTS services with health checks
echo ""
echo "4️⃣ Waiting for TTS services to be ready..."
max_retries=60
for i in $(seq 1 $max_retries); do
    if curl -sf http://localhost:20182/health > /dev/null 2>&1 && \
       curl -sf http://localhost:20183/health > /dev/null 2>&1 && \
       curl -sf http://localhost:20184/health > /dev/null 2>&1; then
        echo "   ✅ All TTS services are online!"
        break
    fi
    
    if [ $i -eq $max_retries ]; then
        echo "   ❌ TTS services failed to start within timeout"
        exit 1
    fi
    
    echo "   ⏳ [$i/$max_retries] Waiting for services..."
    sleep 2
done

# Step 5: Start Flask app in background
echo ""
echo "5️⃣ Starting Flask app on port 5004..."
echo "=================================================="
python app.py >> flask_app.log 2>&1 &
FLASK_PID=$!
echo "   🌐 Flask started (PID: $FLASK_PID)"

# Step 6: Watchdog — monitor all workers and restart if they crash
echo ""
echo "6️⃣ Watchdog active — monitoring all services..."
echo "=================================================="

restart_worker() {
    local GPU=$1
    local PORT=$2
    local LOG=$3
    echo "   🔁 [$(date '+%H:%M:%S')] Restarting TTS GPU $GPU (port $PORT)..."
    python chatterbox_service.py --port $PORT --gpu $GPU >> $LOG 2>&1 &
    eval "CHATTERBOX_${GPU}_PID=$!"
    echo "   ✅ GPU $GPU restarted (PID: ${!})"
}

while true; do
    sleep 10

    # Check GPU 0 worker
    if ! kill -0 $CHATTERBOX_0_PID 2>/dev/null; then
        echo "   ❌ [$(date '+%H:%M:%S')] GPU 0 TTS worker (port 20182) crashed! Restarting..."
        python chatterbox_service.py --port 20182 --gpu 0 >> chatterbox_gpu0.log 2>&1 &
        CHATTERBOX_0_PID=$!
        echo "   ✅ GPU 0 restarted (PID: $CHATTERBOX_0_PID)"
    fi

    # Check GPU 1 worker
    if ! kill -0 $CHATTERBOX_1_PID 2>/dev/null; then
        echo "   ❌ [$(date '+%H:%M:%S')] GPU 1 TTS worker (port 20183) crashed! Restarting..."
        python chatterbox_service.py --port 20183 --gpu 1 >> chatterbox_gpu1.log 2>&1 &
        CHATTERBOX_1_PID=$!
        echo "   ✅ GPU 1 restarted (PID: $CHATTERBOX_1_PID)"
    fi

    # Check GPU 2 worker
    if ! kill -0 $CHATTERBOX_2_PID 2>/dev/null; then
        echo "   ❌ [$(date '+%H:%M:%S')] GPU 2 TTS worker (port 20184) crashed! Restarting..."
        python chatterbox_service.py --port 20184 --gpu 2 >> chatterbox_gpu2.log 2>&1 &
        CHATTERBOX_2_PID=$!
        echo "   ✅ GPU 2 restarted (PID: $CHATTERBOX_2_PID)"
    fi

    # Check Flask app
    if ! kill -0 $FLASK_PID 2>/dev/null; then
        echo "   ❌ [$(date '+%H:%M:%S')] Flask app crashed! Restarting..."
        python app.py >> flask_app.log 2>&1 &
        FLASK_PID=$!
        echo "   ✅ Flask restarted (PID: $FLASK_PID)"
    fi
done
