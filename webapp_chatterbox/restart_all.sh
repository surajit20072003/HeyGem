#!/bin/bash

# Configuration
DIR="/nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox"
VENV="$DIR/chatterbox_venv/bin/python"

# 🔑 API KEY (Replace this with your actual key)
export SARVAM_API_KEY="sk_digx1hbs_nwOqUdNYnWpXstwCsy3YrzQ4"
# Complete restart script for HeyGem Chatterbox
# Handles GPU containers + TTS services + Flask app

set -e

echo "=================================================="
echo "🔄 Full Restart: GPU Containers + Chatterbox"
echo "=================================================="

# Step 1: Stop systemd service
echo ""
echo "1️⃣ Stopping systemd service..."
sudo systemctl stop heygem-chatterbox 2>/dev/null && echo "   ✅ Service stopped" || echo "   ℹ️  Service was not running"

# Step 2: Kill any manual processes
echo ""
echo "2️⃣ Cleaning up manual processes..."
sudo pkill -f "chatterbox_service.py" 2>/dev/null && echo "   🧹 Killed TTS processes" || echo "   ✅ No TTS processes found"
sudo pkill -f "webapp_chatterbox.*app.py" 2>/dev/null && echo "   🧹 Killed Flask processes" || echo "   ✅ No Flask processes found"
sleep 2

# Step 3: Restart Docker containers
echo ""
echo "3️⃣ Restarting GPU containers..."
if sudo systemctl is-active --quiet heygem-chatterbox-containers; then
    echo "   🔄 Using container service..."
    sudo systemctl restart heygem-chatterbox-containers
else
    echo "   🐳 Direct container restart..."
    sudo docker restart heygem-gpu0 heygem-gpu1 heygem-gpu2
fi

# Wait for containers to be ready
echo ""
echo "4️⃣ Waiting for containers to be ready..."
max_wait=30
for i in $(seq 1 $max_wait); do
    all_healthy=true
    for port in 8390 8391 8392; do
        if ! curl -sf http://localhost:$port/health >/dev/null 2>&1; then
            all_healthy=false
            break
        fi
    done
    
    if $all_healthy; then
        echo "   ✅ All containers healthy!"
        break
    fi
    
    if [ $i -eq $max_wait ]; then
        echo "   ⚠️  Containers still not fully ready, but continuing..."
    else
        echo "   ⏳ [$i/$max_wait] Waiting..."
        sleep 2
    fi
done

# Step 5: Start main service
echo ""
echo "5️⃣ Starting heygem-chatterbox service..."
sudo systemctl start heygem-chatterbox
echo "   ✅ Service start command issued"

# Wait for startup
sleep 5

# Step 6: Status check
echo ""
echo "=================================================="
echo "📊 Status Check"
echo "=================================================="

echo ""
echo "🐳 Container Status:"
sudo systemctl status heygem-chatterbox-containers --no-pager 2>/dev/null || echo "   ℹ️  Container service not installed"

echo ""
echo "🎤 Chatterbox Service Status:"
sudo systemctl status heygem-chatterbox --no-pager -l

echo ""
echo "🌐 Port Status:"
echo "   Expected: 5004 (Flask), 8390-8391 (GPU), 20182-20184 (TTS)"
netstat -tlnp 2>/dev/null | grep -E ':(5004|8390|8391|8392|20182|20183|20184)' || \
ss -tlnp | grep -E ':(5004|8390|8391|8392|20182|20183|20184)' || echo "   ⚠️  Could not check ports"

echo ""
echo "=================================================="
echo "✅ Restart Complete!"
echo "=================================================="
echo ""
echo "💡 Quick checks:"
echo "   API:       curl http://localhost:5004/api/health"
echo "   TTS GPU0:  curl http://localhost:20182/health"
echo "   Logs:      sudo journalctl -u heygem-chatterbox -f"
echo ""
