# 🚀 Dual TTS System - Quick Setup Guide

## ✨ What This System Does

This is a **high-performance video generation setup** that uses:
- **2 GPUs** (GPU 0 and GPU 1)
- **2 TTS Containers** (one for each GPU)
- **Port 5003** for web interface
- **No GPU 2 usage** (available for other work)

### Key Advantage: **NO TTS BOTTLENECK!** 🎯

Each GPU has its own dedicated TTS service, so they never wait for each other.

---

## 📦 Prerequisites Check

Before starting, make sure you have:

- [ ] Docker installed
- [ ] NVIDIA Container Toolkit installed
- [ ] 2 NVIDIA GPUs (GPU 0 and GPU 1)
- [ ] Python 3.8+
- [ ] ffmpeg installed

---

## 🎬 Complete Setup in 5 Steps

### Step 1: Create Data Directories

```bash
cd /nvme0n1-disk/nvme01/HeyGem

# Create required directories
mkdir -p /home/administrator/heygem_data/gpu0
mkdir -p /home/administrator/heygem_data/gpu1
mkdir -p /home/administrator/heygem_data/tts0
mkdir -p /home/administrator/heygem_data/tts1
```

### Step 2: Start Docker Containers

```bash
# Start all 4 containers (2 GPU + 2 TTS)
docker-compose -f docker-compose-dual-tts.yml up -d

# Wait 1-2 minutes for initialization

# Check status - you should see 4 containers
docker ps
```

**Expected Output:**
```
CONTAINER ID   IMAGE                           STATUS    PORTS
xxxxx          guiji2025/heygem.ai             Up        0.0.0.0:8390->8383/tcp
xxxxx          guiji2025/heygem.ai             Up        0.0.0.0:8391->8383/tcp
xxxxx          guiji2025/fish-speech-ziming    Up        0.0.0.0:18180->8080/tcp
xxxxx          guiji2025/fish-speech-ziming    Up        0.0.0.0:18181->8080/tcp
```

### Step 3: Install Python Dependencies

```bash
cd webapp_dual_tts
pip install -r requirements.txt
```

### Step 4: Test the System

```bash
# Run system test
python3 test_system.py
```

**Expected Output:**
```
🧪 Testing TTS Service 0 (Port 18180)...
   ✅ TTS Service 0 (GPU 0) is responding

🧪 Testing TTS Service 1 (Port 18181)...
   ✅ TTS Service 1 (GPU 1) is responding

🧪 Testing GPU 0 Container (Port 8390)...
   ✅ GPU 0 container is responding

🧪 Testing GPU 1 Container (Port 8391)...
   ✅ GPU 1 container is responding

✅ All tests PASSED! System is ready!
```

### Step 5: Start the Webapp

**Option A - Quick Start Script:**
```bash
./start.sh
```

**Option B - Manual Start:**
```bash
python3 app.py
```

**You should see:**
```
🚀 Dual GPU + Dual TTS Video Generation API Server
📍 Running on: http://0.0.0.0:5003
🎬 GPU Configuration:
   - GPU 0: Video Port 8390, TTS Port 18180
   - GPU 1: Video Port 8391, TTS Port 18181
🎤 Dedicated TTS per GPU - No bottleneck!
```

---

## 🌐 Open Browser

Navigate to: **http://localhost:5003**

You should see a beautiful interface with:
- GPU status cards (showing GPU 0 and GPU 1)
- Upload section (drag & drop)
- Queue status

---

## 🧪 Quick Test

### Test 1: Check API Info
```bash
curl http://localhost:5003/api/info
```

**Expected Response:**
```json
{
  "service": "Dual GPU + Dual TTS Video Generation",
  "version": "1.0.0",
  "port": 5003,
  "gpus": {
    "0": {"video_port": 8390, "tts_port": 18180},
    "1": {"video_port": 8391, "tts_port": 18181}
  }
}
```

### Test 2: Check Queue Status
```bash
curl http://localhost:5003/api/queue
```

### Test 3: Generate a Video
```bash
curl -X POST http://localhost:5003/api/generate \
  -F "video=@/path/to/your/video.mp4" \
  -F "text=Hello, this is a test of the dual TTS system"
```

---

## 📊 System Architecture

```
User Upload (Video + Text)
       ↓
Extract Audio from Video
       ↓
[Smart GPU Selection]
       ↓
┌──────────────────┬──────────────────┐
│   GPU 0 Free?    │   GPU 1 Free?    │
│   Use TTS 18180  │   Use TTS 18181  │
└──────────────────┴──────────────────┘
       ↓                   ↓
Generate Voice Clone (No Waiting!)
       ↓
Queue to Available GPU
       ↓
Process Video Generation
       ↓
Return Final Video
```

---

## 🔧 Troubleshooting

### Issue: Containers not starting

```bash
# Check Docker status
sudo systemctl status docker

# Check GPU availability
nvidia-smi

# View container logs
docker logs heygem-tts-0
docker logs heygem-gpu0
```

### Issue: Port already in use

```bash
# Find what's using port 5003
sudo lsof -i :5003

# Kill the process
sudo kill -9 <PID>
```

### Issue: TTS not responding

```bash
# Restart TTS containers
docker restart heygem-tts-0
docker restart heygem-tts-1

# Wait 30 seconds, then test
curl http://localhost:18180/
curl http://localhost:18181/
```

### Issue: GPU out of memory

```bash
# Check GPU memory
nvidia-smi

# If needed, restart GPU containers
docker restart heygem-gpu0
docker restart heygem-gpu1
```

---

## 📁 File Structure

```
webapp_dual_tts/
├── app.py                      # Flask API server (Port 5003)
├── dual_gpu_scheduler.py       # GPU scheduler with dual TTS
├── text_normalization.py       # Text preprocessing
├── requirements.txt            # Python dependencies
├── README.md                   # Full documentation
├── start.sh                    # Quick start script
├── test_system.py             # System test script
├── static/
│   └── index.html             # Web interface
├── uploads/                   # Uploaded videos
├── outputs/                   # Generated videos
└── temp/                      # Temporary files
```

---

## 🎯 Port Mapping Summary

| Service | Port | Purpose |
|---------|------|---------|
| **Webapp** | 5003 | Web UI + API |
| **GPU 0 Video** | 8390 | Video generation |
| **GPU 1 Video** | 8391 | Video generation |
| **TTS 0** | 18180 | Voice cloning (GPU 0) |
| **TTS 1** | 18181 | Voice cloning (GPU 1) |

---

## ⚡ Performance Tips

### Maximize Throughput
1. Keep both GPUs warm by submitting tasks in batches
2. Use shorter texts for faster TTS processing
3. Monitor queue status regularly

### Optimize Quality
1. Use high-quality reference videos (1080p+)
2. Clear audio with minimal background noise
3. Text should match the reference speaker's style

---

## 🔄 Starting/Stopping

### Start Everything
```bash
# Start Docker containers
docker-compose -f docker-compose-dual-tts.yml up -d

# Start webapp
cd webapp_dual_tts
./start.sh
```

### Stop Everything
```bash
# Stop webapp (Ctrl+C if running in terminal)

# Stop Docker containers
docker-compose -f docker-compose-dual-tts.yml down
```

### Restart Everything
```bash
# Restart containers
docker-compose -f docker-compose-dual-tts.yml restart

# Restart webapp
cd webapp_dual_tts
./start.sh
```

---

## 📝 Common Use Cases

### Generate Single Video
1. Open http://localhost:5003
2. Drag & drop video
3. Enter text
4. Click "Generate Video"
5. Monitor progress
6. Download when complete

### Batch Processing
Submit multiple videos via API:
```bash
for video in *.mp4; do
  curl -X POST http://localhost:5003/api/generate \
    -F "video=@$video" \
    -F "text=Your text here"
  sleep 2
done
```

### Monitor Queue
Watch queue in real-time:
```bash
watch -n 2 'curl -s http://localhost:5003/api/queue | jq'
```

---

## 🎉 You're Ready!

Your dual TTS system is now running! Features:

✅ 2 GPUs for video generation  
✅ 2 TTS services (no bottleneck)  
✅ Modern web interface  
✅ Automatic queue management  
✅ Real-time status monitoring  

**Open:** http://localhost:5003

Happy video generation! 🚀
