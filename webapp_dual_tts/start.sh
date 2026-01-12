#!/bin/bash
# Quick Start Script for Dual TTS System
# Run this after Docker containers are up

echo "=========================================="
echo "🚀 Starting Dual TTS Webapp System"
echo "=========================================="

# Check if Docker containers are running
echo ""
echo "📦 Checking Docker containers..."
docker ps | grep -E "heygem-(gpu|tts)" || {
    echo "❌ Docker containers not found!"
    echo "Run: docker-compose -f docker-compose-dual-tts.yml up -d"
    exit 1
}

echo "✅ Docker containers are running"

# Create directories if they don't exist
echo ""
echo "📁 Creating directories..."
mkdir -p uploads outputs temp static

# Check Python dependencies
echo ""
echo "📦 Checking Python dependencies..."
pip install -q -r requirements.txt

echo "✅ Dependencies ready"

# Start the webapp
echo ""
echo "=========================================="
echo "🎬 Starting Webapp on Port 5003"
echo "=========================================="
echo ""
echo "Open browser: http://localhost:5003"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 app.py
