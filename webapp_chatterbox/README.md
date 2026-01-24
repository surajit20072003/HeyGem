# Triple GPU + Triple TTS Video Generation System

## 🚀 Overview

This webapp provides **high-performance video generation** with dedicated TTS services for each GPU:

- **GPU 0** (Port 8390) → **TTS 0** (Port 18182)
- **GPU 1** (Port 8391) → **TTS 1** (Port 18183)
- **GPU 2** (Port 8392) → **TTS 2** (Port 18184)
- **Web API** running on **Port 5003**

## ✨ Key Features

✅ **3 GPUs, 3 TTS Services** - Maximum throughput!  
✅ **Smart Queue Management** - Automatic task distribution  
✅ **Dedicated TTS per GPU** - No bottlenecks  
✅ **Real-time Status** - Monitor all GPUs and queue  
✅ **Modern Web UI** - Drag & drop interface  
✅ **Text Normalization** - LaTeX/Math conversion support

---

## 🏗️ Architecture

```
User Request (Video + Text)
    ↓
Extract Audio from Video
    ↓
[Smart GPU Selection - 3 GPUs Available]
    ↓
GPU 0 Free → Use TTS Port 18182
GPU 1 Free → Use TTS Port 18183
GPU 2 Free → Use TTS Port 18184
    ↓
Generate Voice Clone (Dedicated TTS)
    ↓
Queue to Available GPU
    ↓
Process Video
    ↓
Return Result
```

**Advantage**: Each GPU has its own TTS service, so:
- No waiting for shared TTS
- True parallel processing (3 videos simultaneously)
- 50% faster than dual GPU setup

---

## 📦 Prerequisites

### 1. Docker Containers Required

You need **6 Docker containers** running:

**GPU Containers:**
```bash
heygem-gpu0  → Port 8390 (GPU 0)
heygem-gpu1  → Port 8391 (GPU 1)
heygem-gpu2  → Port 8392 (GPU 2)
```

**TTS Containers:**
```bash
heygem-tts-dual-0 → Port 18182 (Fish-Speech for GPU 0)
heygem-tts-dual-1 → Port 18183 (Fish-Speech for GPU 1)
heygem-tts-dual-2 → Port 18184 (Fish-Speech for GPU 2)
```

### 2. System Requirements

- **3 NVIDIA GPUs** (RTX A5000 or similar)
- **Docker** with NVIDIA runtime
- **Python 3.8+** with Flask
- **FFmpeg** for audio/video processing

---

## 🎬 How to Run

### Step 1: Create Data Directories

```bash
# Create data directories for all GPUs and TTS services
mkdir -p ~/heygem_data/{gpu0,gpu1,gpu2,tts0,tts1,tts2}
```

### Step 2: Start Docker Containers

```bash
# Navigate to project directory
cd /nvme0n1-disk/nvme01/HeyGem

# Start all containers
docker compose -f docker-compose-dual-tts.yml up -d

# Verify all 6 containers are running
docker ps --filter "name=heygem"
```

You should see:
```
heygem-gpu0
heygem-gpu1
heygem-gpu2
heygem-tts-dual-0
heygem-tts-dual-1
heygem-tts-dual-2
```

### Step 3: Install Python Dependencies

```bash
cd webapp_dual_tts
pip install -r requirements.txt
```

### Step 4: Start the Web Server

```bash
# Using systemd service (recommended)
sudo systemctl start heygem-dual-tts
sudo systemctl enable heygem-dual-tts  # Auto-start on boot

# OR manually
python3 app.py
```

### Step 5: Open Browser

```
http://localhost:5003
```

---

## 🔌 API Endpoints

### 1. Generate Video
```bash
POST /api/generate
Content-Type: multipart/form-data

Fields:
  - video: Video file (optional)
  - text: Text to speak (required)

Response:
{
  "success": true,
  "task_id": "task_1234567890",
  "status_url": "/api/status/task_1234567890"
}
```

### 2. Check Status
```bash
GET /api/status/{task_id}

Response:
{
  "status": "processing|completed|failed|queued",
  "progress": 0-100,
  "gpu_id": 0|1|2,
  "timing": {
    "tts_time": 26.5,
    "video_time": 65.3,
    "total_time": 91.8
  }
}
```

### 3. Get Queue Status
```bash
GET /api/queue

Response:
{
  "gpus": {
    "0": {"busy": true, "current_task": "task_123", ...},
    "1": {"busy": false, "current_task": null, ...},
    "2": {"busy": true, "current_task": "task_456", ...}
  },
  "queue": [],
  "queue_size": 0
}
```

### 4. Download Video
```bash
GET /api/download/{task_id}
```

### 5. API Info
```bash
GET /api/info

Response:
{
  "service": "Triple GPU + Triple TTS Video Generation",
  "gpus": {
    "0": {"video_port": 8390, "tts_port": 18182},
    "1": {"video_port": 8391, "tts_port": 18183},
    "2": {"video_port": 8392, "tts_port": 18184}
  }
}
```

---

## 📊 Performance Comparison

| Setup | GPUs | TTS Services | Max Parallel Videos | Throughput |
|-------|------|--------------|---------------------|------------|
| Single GPU | 1 | 1 | 1 video | Baseline |
| Dual GPU | 2 | 2 | 2 videos | 2x faster |
| **Triple GPU** | **3** | **3** | **3 videos** | **3x faster** |

---

## 🧪 Testing

### Test with cURL

```bash
# Test all TTS services
curl -X POST http://localhost:18182/v1/health
curl -X POST http://localhost:18183/v1/health
curl -X POST http://localhost:18184/v1/health

# Submit video generation
curl -X POST http://localhost:5003/api/generate \
  -F "video=@test.mp4" \
  -F "text=Hello, this is a test"

# Check status
curl http://localhost:5003/api/status/task_xxxxx

# View queue
curl http://localhost:5003/api/queue
```

### Test 3 Parallel Tasks

```bash
# Submit 3 tasks simultaneously
for i in {1..3}; do
  curl -X POST http://localhost:5003/api/generate \
    -F "text=Test video $i" &
done

# All 3 should process in parallel (no queue)
curl http://localhost:5003/api/queue
```

---

## 🔧 Configuration

### GPU Assignment

Edit `dual_gpu_scheduler.py`:

```python
self.gpu_config = {
    0: {
        "port": 8390,      # Video generation port
        "tts_port": 18182, # Dedicated TTS port
        "busy": False
    },
    1: {
        "port": 8391,
        "tts_port": 18183,
        "busy": False
    },
    2: {
        "port": 8392,
        "tts_port": 18184,
        "busy": False
    }
}
```

### Timeout Settings

```python
max_wait = 1800  # 30 minutes
check_interval = 5  # Check every 5 seconds
```

---

## 🐛 Troubleshooting

### Issue: TTS Service Not Responding

```bash
# Check TTS containers
docker logs heygem-tts-dual-0
docker logs heygem-tts-dual-1
docker logs heygem-tts-dual-2

# Restart if needed
docker restart heygem-tts-dual-0
docker restart heygem-tts-dual-1
docker restart heygem-tts-dual-2
```

### Issue: GPU Container Stuck (Returns "BUSY")

**Symptoms**: Container always returns "忙碌中" (busy), zombie processes

**Solution**:
```bash
# Check for zombie processes
docker exec heygem-gpu2 ps aux | grep defunct

# Restart the stuck container
docker restart heygem-gpu2

# Wait 30 seconds for initialization
sleep 30

# Verify it's working
curl -s http://localhost:8392/easy/query?code=test123
```

### Issue: GPU Not Found

```bash
# Check GPU visibility
nvidia-smi

# Check container GPU access
docker exec heygem-gpu0 nvidia-smi
docker exec heygem-gpu1 nvidia-smi
docker exec heygem-gpu2 nvidia-smi
```

### Issue: Port Already in Use

```bash
# Find process using port 5003
sudo lsof -i :5003

# Kill process
sudo kill -9 <PID>

# Or use systemd to manage the service
sudo systemctl restart heygem-dual-tts
```

### Issue: Video Not Generating on Specific GPU

```bash
# Check if default.mp4 exists in GPU folder
ls -lh ~/heygem_data/gpu0/default.mp4
ls -lh ~/heygem_data/gpu1/default.mp4
ls -lh ~/heygem_data/gpu2/default.mp4

# Check container can access files
docker exec heygem-gpu0 ls -lh /code/data/
docker exec heygem-gpu1 ls -lh /code/data/
docker exec heygem-gpu2 ls -lh /code/data/

# View container logs for errors
docker logs heygem-gpu0 --tail 50
docker logs heygem-gpu1 --tail 50
docker logs heygem-gpu2 --tail 50
```

---

## 📁 File Structure

```
webapp_dual_tts/
├── app.py                      # Flask API server (Triple GPU)
├── dual_gpu_scheduler.py       # Triple GPU scheduler
├── text_normalization.py       # LaTeX/Math to speech
├── requirements.txt            # Python dependencies
├── static/
│   └── index.html              # Web interface (Triple GPU UI)
├── uploads/                    # User uploaded videos
├── outputs/                    # Generated videos
├── temp/                       # Temporary audio files
├── default.mp4                 # Default video template
└── reference_audio.wav         # Default voice reference
```

---

## 🚀 Advantages Over Other Modes

### vs Dual GPU Mode
- ✅ 50% more throughput (3 vs 2 simultaneous videos)
- ✅ Better GPU utilization
- ✅ Reduced queue wait times

### vs Chunked Mode
- ✅ Simpler architecture (no chunking complexity)
- ✅ Better for short-to-medium videos
- ✅ More reliable (fewer failure points)

---

## 📝 Notes

- **All 3 GPUs active** - maximum parallel processing
- **3 TTS containers** required (ports 18182, 18183, 18184)
- **Smart TTS selection** based on GPU availability
- **Proper queue management** ensures tasks are processed efficiently
- **File stability checks** prevent incomplete file errors

---

## 🎯 Use Cases

**Best for:**
- Production environments requiring maximum throughput
- High-volume video generation workloads
- Scenarios with 3+ available GPUs
- Applications needing minimal latency

**Not recommended for:**
- Systems with only 1-2 GPUs (use dual GPU mode)
- Memory-constrained systems (<16GB VRAM per GPU)
- Long videos requiring chunking (use chunked mode)

---

## 📞 Support

**Check Logs:**
```bash
# Service logs
sudo journalctl -u heygem-dual-tts -f

# Container logs
docker logs heygem-gpu0 -f
docker logs heygem-tts-dual-0 -f

# GPU status
nvidia-smi -l 1
```

**Monitor System:**
- Web UI: `http://localhost:5003`
- Queue API: `http://localhost:5003/api/queue`
- Health Check: `http://localhost:5003/api/health`

---

**Ready to use! Process 3 videos simultaneously! 🎉**
