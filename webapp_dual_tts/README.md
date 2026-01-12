# Dual GPU + Dual TTS Video Generation System

## 🚀 Overview

This webapp provides **high-performance video generation** with dedicated TTS services for each GPU:

- **GPU 0** (Port 8390) → **TTS 0** (Port 18182)
- **GPU 1** (Port 8391) → **TTS 1** (Port 18183)
- **Web API** running on **Port 5003**

## ✨ Key Features

✅ **2 GPUs, 2 TTS Services** - No bottlenecks!  
✅ **Smart Queue Management** - Automatic task distribution  
✅ **Dedicated TTS per GPU** - Faster processing  
✅ **Real-time Status** - Monitor GPUs and queue  
✅ **Modern Web UI** - Drag & drop interface

---

## 🏗️ Architecture

```
User Request (Video + Text)
    ↓
Extract Audio from Video
    ↓
[Smart GPU Selection]
    ↓
GPU 0 Free → Use TTS Port 18180
GPU 1 Free → Use TTS Port 18181
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
- Parallel processing of audio + video
- Faster overall pipeline

---

## 📦 Prerequisites

### 1. Docker Containers Required

You need **4 Docker containers** running:

**GPU Containers:**
```bash
heygem-gpu0  → Port 8390 (GPU 0)
heygem-gpu1  → Port 8391 (GPU 1)
```

**TTS Containers:**
```bash
heygem-tts-0 → Port 18180 (Fish-Speech for GPU 0)
heygem-tts-1 → Port 18181 (Fish-Speech for GPU 1)
```

### 2. Docker Compose Configuration

Create a new `docker-compose-dual-tts.yml`:

```yaml
version: '3.8'

networks:
  heygem_network:
    driver: bridge

services:
  # GPU 0 - Video Generation
  heygem-gpu0:
    image: guiji2025/heygem.ai
    container_name: heygem-gpu0
    restart: always
    runtime: nvidia
    privileged: true
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']
              capabilities: [gpu]
    shm_size: '8g'
    ports:
      - '8390:8383'
    volumes:
      - ~/heygem_data/gpu0:/code/data
    command: python /code/app_local.py
    networks:
      - heygem_network

  # GPU 1 - Video Generation
  heygem-gpu1:
    image: guiji2025/heygem.ai
    container_name: heygem-gpu1
    restart: always
    runtime: nvidia
    privileged: true
    environment:
      - CUDA_VISIBLE_DEVICES=1
      - PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']
              capabilities: [gpu]
    shm_size: '8g'
    ports:
      - '8391:8383'
    volumes:
      - ~/heygem_data/gpu1:/code/data
    command: python /code/app_local.py
    networks:
      - heygem_network

  # TTS Service for GPU 0
  heygem-tts-0:
    image: guiji2025/fish-speech-ziming
    container_name: heygem-tts-0
    restart: always
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
      - NVIDIA_DRIVER_CAPABILITIES=compute,graphics,utility,video,display
    ports:
      - '18180:8080'
    volumes:
      - ~/heygem_data/tts0:/code/data
    command: /bin/bash -c "/opt/conda/envs/python310/bin/python3 tools/api_server.py --listen 0.0.0.0:8080"
    networks:
      - heygem_network

  # TTS Service for GPU 1
  heygem-tts-1:
    image: guiji2025/fish-speech-ziming
    container_name: heygem-tts-1
    restart: always
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=1
      - NVIDIA_DRIVER_CAPABILITIES=compute,graphics,utility,video,display
    ports:
      - '18181:8080'
    volumes:
      - ~/heygem_data/tts1:/code/data
    command: /bin/bash -c "/opt/conda/envs/python310/bin/python3 tools/api_server.py --listen 0.0.0.0:8080"
    networks:
      - heygem_network
```

---

## 🎬 How to Run

### Step 1: Start Docker Containers

```bash
# Create data directories
mkdir -p ~/heygem_data/{gpu0,gpu1,tts0,tts1}

# Start containers
docker-compose -f docker-compose-dual-tts.yml up -d

# Check status
docker ps
```

You should see 4 containers running:
```
heygem-gpu0
heygem-gpu1
heygem-tts-0
heygem-tts-1
```

### Step 2: Install Python Dependencies

```bash
cd webapp_dual_tts
pip install -r requirements.txt
```

### Step 3: Start the Web Server

```bash
python3 app.py
```

### Step 4: Open Browser

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
  - video: Video file
  - text: Text to speak

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
  "status": "processing",
  "progress": 45,
  "gpu_id": 0,
  "queue_position": null
}
```

### 3. Get Queue Status
```bash
GET /api/queue

Response:
{
  "gpus": {
    "0": {
      "busy": true,
      "current_task": "task_123",
      "tts_port": 18180,
      "video_port": 8390
    },
    "1": {
      "busy": false,
      "current_task": null,
      "tts_port": 18181,
      "video_port": 8391
    }
  },
  "queue": [],
  "queue_size": 0
}
```

### 4. Download Video
```bash
GET /api/download/{task_id}
```

---

## 📊 Performance Comparison

| Setup | TTS Bottleneck | Max Parallel Videos | Speed |
|-------|----------------|---------------------|-------|
| **Single TTS** | ✅ Yes | 2-3 videos | Normal |
| **Dual TTS** | ❌ No | 2 videos | **Faster** |

**Why Faster?**
- Each GPU gets its own TTS service
- No waiting for TTS to be free
- True parallel processing

---

## 🧪 Testing

### Test with cURL

```bash
# Test GPU 0 TTS
curl -X POST http://localhost:18180/health

# Test GPU 1 TTS
curl -X POST http://localhost:18181/health

# Submit video generation
curl -X POST http://localhost:5003/api/generate \
  -F "video=@test.mp4" \
  -F "text=Hello, this is a test"

# Check status
curl http://localhost:5003/api/status/task_xxxxx

# View queue
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
        "tts_port": 18180, # Dedicated TTS port
        "busy": False
    },
    1: {
        "port": 8391,
        "tts_port": 18181,
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
docker logs heygem-tts-0
docker logs heygem-tts-1

# Restart if needed
docker restart heygem-tts-0
docker restart heygem-tts-1
```

### Issue: GPU Not Found

```bash
# Check GPU visibility
nvidia-smi

# Check container GPU access
docker exec heygem-gpu0 nvidia-smi
docker exec heygem-gpu1 nvidia-smi
```

### Issue: Port Already in Use

```bash
# Find process using port 5003
sudo lsof -i :5003

# Kill process
sudo kill -9 <PID>
```

---

## 📁 File Structure

```
webapp_dual_tts/
├── app.py                    # Flask API server
├── dual_gpu_scheduler.py     # Dual GPU scheduler
├── requirements.txt          # Python dependencies
├── static/
│   └── index.html            # Web interface
├── uploads/                  # User uploaded videos
├── outputs/                  # Generated videos
└── temp/                     # Temporary audio files
```

---

## 🚀 Advantages Over Other Modes

### vs Simple Mode (Port 5000)
- ✅ Dedicated TTS per GPU (no bottleneck)
- ✅ Only 2 GPUs (GPU 2 free for other tasks)

### vs Chunked Mode (Port 5001)
- ✅ Simpler architecture (no chunking complexity)
- ✅ Better for short-to-medium videos
- ✅ Dedicated TTS services

---

## 📝 Notes

- **GPU 2 is NOT used** - available for other tasks
- **2 TTS containers** required (18180 and 18181)
- **Smart TTS selection** based on GPU availability
- **Proper queue management** ensures tasks are processed efficiently

---

## 🎯 Use Cases

**Best for:**
- Production environments with 2 active GPUs
- Scenarios where GPU 2 is reserved for other work
- High-throughput video generation
- Minimal TTS bottlenecks

---

## 📞 Support

For issues or questions:
- Check logs: `docker logs heygem-gpu0`
- Monitor queue: `http://localhost:5003/api/queue`
- GPU status: `nvidia-smi`

---

**Ready to use! Happy video generation! 🎉**
