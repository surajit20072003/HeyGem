#!/bin/bash
# Startup script for webapp_chatterbox
# Starts 3 Chatterbox TTS services + Flask app

echo "=========================================="
echo "🚀 Starting Chatterbox TTS Services"
echo "=========================================="

# Start Chatterbox TTS services on each GPU
echo "📍 Starting Chatterbox TTS 0 on GPU 0 (Port 20182)..."
python3 chatterbox_service.py --port 20182 --gpu 0 &
CHATTERBOX_0_PID=$!

echo "📍 Starting Chatterbox TTS 1 on GPU 1 (Port 20183)..."
python3 chatterbox_service.py --port 20183 --gpu 1 &
CHATTERBOX_1_PID=$!

echo "📍 Starting Chatterbox TTS 2 on GPU 2 (Port 20184)..."
python3 chatterbox_service.py --port 20184 --gpu 2 &
CHATTERBOX_2_PID=$!

# Wait for TTS services to initialize
echo "⏳ Waiting for Chatterbox services to initialize..."
sleep 10

# Check if services are running
echo "🔍 Checking Chatterbox service health..."
curl -s http://localhost:20182/ > /dev/null && echo "✅ Chatterbox TTS 0 is running" || echo "❌ Chatterbox TTS 0 failed to start"
curl -s http://localhost:20183/ > /dev/null && echo "✅ Chatterbox TTS 1 is running" || echo "❌ Chatterbox TTS 1 failed to start"
curl -s http://localhost:20184/ > /dev/null && echo "✅ Chatterbox TTS 2 is running" || echo "❌ Chatterbox TTS 2 failed to start"

echo ""
echo "=========================================="
echo "🌐 Starting Flask Web Application"
echo "=========================================="

# Start Flask app
python3 app.py

# Cleanup on exit
trap "kill $CHATTERBOX_0_PID $CHATTERBOX_1_PID $CHATTERBOX_2_PID 2>/dev/null" EXIT
