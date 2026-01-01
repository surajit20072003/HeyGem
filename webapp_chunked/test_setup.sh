#!/bin/bash
# Quick test script for chunked webapp

echo "=========================================="
echo "Chunked Webapp - Quick Test"
echo "=========================================="

cd /nvme0n1-disk/HeyGem/webapp_chunked

echo ""
echo "1. Checking directory structure..."
if [ -f "app.py" ] && [ -f "chunked_scheduler.py" ] && [ -f "static/index.html" ]; then
    echo "   ✅ All required files present"
else
    echo "   ❌ Missing files!"
    exit 1
fi

echo ""
echo "2. Checking Python dependencies..."
python3 -c "import flask, flask_cors, requests, psutil" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ All Python packages installed"
else
    echo "   ⚠️  Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "3. Checking GPU containers..."
for port in 8390 8391 8392; do
    curl -s http://127.0.0.1:$port/health > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ GPU container on port $port is running"
    else
        echo "   ⚠️  GPU container on port $port might not be running"
    fi
done

echo ""
echo "4. Checking TTS service..."
curl -s http://127.0.0.1:18181/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ TTS service (port 18181) is running"
else
    echo "   ⚠️  TTS service might not be running"
fi

echo ""
echo "5. Checking FFmpeg with NVENC support..."
ffmpeg -encoders 2>&1 | grep -q "h264_nvenc"
if [ $? -eq 0 ]; then
    echo "   ✅ FFmpeg has NVENC support"
else
    echo "   ⚠️  FFmpeg might not have NVENC support"
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "To start the chunked webapp:"
echo "  cd /nvme0n1-disk/HeyGem/webapp_chunked"
echo "  python3 app.py"
echo ""
echo "Then open: http://localhost:5001"
echo ""
echo "Regular webapp (queue mode): http://localhost:5000"
echo "Chunked webapp (parallel mode): http://localhost:5001"
echo "=========================================="
