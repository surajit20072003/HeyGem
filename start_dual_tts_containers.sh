#!/bin/bash
# Script to start new dual TTS containers (ports 18182/18183)
# Existing containers will NOT be affected

echo "=============================================="
echo "🚀 Starting Dual TTS Containers"
echo "=============================================="
echo ""
echo "New Containers:"
echo "  - heygem-tts-dual-0 (Port 18182, GPU 0)"
echo "  - heygem-tts-dual-1 (Port 18183, GPU 1)"
echo ""
echo "Existing containers will remain running!"
echo ""

# Start dual TTS containers using docker compose (V2 syntax)
cd /nvme0n1-disk/nvme01/HeyGem

docker compose -f docker-compose-dual-tts.yml up -d heygem-tts-dual-0 heygem-tts-dual-1

echo ""
echo "⏳ Waiting 10 seconds for containers to initialize..."
sleep 10

echo ""
echo "=============================================="
echo "📊 Container Status"
echo "=============================================="
docker ps --filter "name=heygem" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "✅ Dual TTS containers started!"
echo ""
echo "Test with:"
echo "  curl http://localhost:18182/"
echo "  curl http://localhost:18183/"
echo ""
