# Complete Triple GPU System Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Installation Guide](#installation-guide)
4. [Configuration](#configuration)
5. [Usage & API](#usage--api)
6. [Monitoring & Debugging](#monitoring--debugging)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## System Overview

### What is Triple GPU + Triple TTS?

A high-performance video generation system that processes **3 videos simultaneously** using:
- **3 NVIDIA GPUs** for video processing
- **3 dedicated TTS services** for voice cloning
- **Smart scheduler** for optimal task distribution
- **Web API + UI** for easy interaction

### Key Specifications

| Component | Value |
|-----------|-------|
| **GPUs** | 3x NVIDIA RTX A5000 (24GB VRAM each) |
| **TTS Services** | 3x Fish-Speech containers |
| **Max Throughput** | 3 videos simultaneously |
| **API Port** | 5003 |
| **GPU Ports** | 8390, 8391, 8392 |
| **TTS Ports** | 18182, 18183, 18184 |

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Browser (User)                       │
│                  http://localhost:5003                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Flask API Server (Port 5003)                   │
│              webapp_dual_tts/app.py                         │
│                                                             │
│  Routes:                                                    │
│  • POST /api/generate    - Submit video task               │
│  • GET  /api/status/:id  - Check task status               │
│  • GET  /api/queue       - View GPU status & queue         │
│  • GET  /api/download/:id - Download result                │
└───────────────────┬──────────────────┬──────────────────────┘
                    │                  │
                    ▼                  ▼
┌───────────────────────────┐  ┌──────────────────────────────┐
│  Triple GPU Scheduler     │  │  Text Normalization          │
│  dual_gpu_scheduler.py    │  │  text_normalization.py       │
│                           │  │                              │
│  • GPU reservation        │  │  • LaTeX → Speech            │
│  • Task queuing           │  │  • Math notation conversion  │
│  • Load balancing         │  │  • Number → Words            │
│  • Progress monitoring    │  └──────────────────────────────┘
└───────┬────────┬──────┬──┘
        │        │      │
    ┌───▼───┐┌──▼───┐┌─▼────┐
    │ GPU 0 ││ GPU 1││ GPU 2│
    │ :8390 ││ :8391││ :8392│
    └───┬───┘└──┬───┘└─┬────┘
        │       │      │
    ┌───▼───┐┌──▼───┐┌─▼────┐
    │ TTS 0 ││ TTS 1││ TTS 2│
    │:18182 ││:18183││:18184│
    └───────┘└──────┘└──────┘
```

### Data Flow

```
1. User submits text + video (optional)
   ↓
2. Extract audio from video OR use default reference
   ↓
3. Reserve available GPU atomically
   ↓
4. Generate voice clone using GPU's dedicated TTS
   ↓
5. Submit video + audio to reserved GPU
   ↓
6. Monitor task progress
   ↓
7. Return result when complete
   ↓
8. Release GPU for next task
```

### File System Structure

```
/nvme0n1-disk/nvme01/HeyGem/
├── webapp_dual_tts/              # Main application
│   ├── app.py                     # Flask API server
│   ├── dual_gpu_scheduler.py      # GPU scheduler
│   ├── text_normalization.py      # Text preprocessing
│   ├── static/index.html          # Web UI
│   ├── uploads/                   # User uploads
│   ├── outputs/                   # Final videos
│   └── temp/                      # TTS audio files
│
└── ~/heygem_data/                 # Shared data (Docker volumes)
    ├── gpu0/                      # GPU 0 data dir
    │   ├── default.mp4
    │   ├── temp/
    │   └── result/
    ├── gpu1/                      # GPU 1 data dir
    ├── gpu2/                      # GPU 2 data dir
    ├── tts0/                      # TTS 0 data dir
    │   └── reference/
    ├── tts1/                      # TTS 1 data dir
    └── tts2/                      # TTS 2 data dir
```

---

## Installation Guide

### Prerequisites

#### Hardware Requirements
- **CPU**: Intel i5-13400F or better
- **RAM**: 32GB minimum, 64GB recommended
- **GPU**: 3x NVIDIA GPUs with 16GB+ VRAM each
- **Storage**: 200GB free space (100GB for Docker images)
- **Network**: Stable internet for Docker pulls

#### Software Requirements
- **OS**: Ubuntu 22.04 LTS (tested) or similar Linux
- **Docker**: 20.10+ with NVIDIA Container Toolkit
- **Python**: 3.8+
- **NVIDIA Driver**: 560.31.02 or compatible
- **CUDA**: 12.6 or compatible

### Step-by-Step Installation

#### 1. Install NVIDIA Drivers & CUDA

```bash
# Check current driver
nvidia-smi

# If driver not installed or outdated:
sudo ubuntu-drivers devices
sudo ubuntu-drivers autoinstall
sudo reboot
```

#### 2. Install Docker with NVIDIA Runtime

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Test NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

#### 3. Create Data Directories

```bash
# Create all required directories
mkdir -p ~/heygem_data/{gpu0,gpu1,gpu2,tts0,tts1,tts2}

# Create subdirectories
for i in 0 1 2; do
  mkdir -p ~/heygem_data/gpu$i/{temp,result,log}
  mkdir -p ~/heygem_data/tts$i/reference
done

# Set permissions
chmod -R 755 ~/heygem_data
```

#### 4. Pull Docker Images

```bash
# Pull heygem.ai image (GPU containers)
docker pull guiji2025/heygem.ai

# Pull Fish-Speech image (TTS containers)
docker pull guiji2025/fish-speech-ziming

# Verify images
docker images | grep -E "heygem|fish"
```

#### 5. Start Docker Containers

```bash
cd /nvme0n1-disk/nvme01/HeyGem

# Start all 6 containers
docker compose -f docker-compose-dual-tts.yml up -d

# Wait for containers to initialize (30-60 seconds)
sleep 60

# Verify all containers are running
docker ps --filter "name=heygem" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected output:
```
NAMES               STATUS          PORTS
heygem-gpu0         Up 2 minutes    0.0.0.0:8390->8383/tcp
heygem-gpu1         Up 2 minutes    0.0.0.0:8391->8383/tcp
heygem-gpu2         Up 2 minutes    0.0.0.0:8392->8383/tcp
heygem-tts-dual-0   Up 2 minutes    0.0.0.0:18182->8080/tcp
heygem-tts-dual-1   Up 2 minutes    0.0.0.0:18183->8080/tcp
heygem-tts-dual-2   Up 2 minutes    0.0.0.0:18184->8080/tcp
```

#### 6. Setup Python Environment

```bash
cd webapp_dual_tts

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 7. Setup Systemd Service (Optional)

```bash
# Create service file
sudo nano /etc/systemd/system/heygem-dual-tts.service
```

Paste:
```ini
[Unit]
Description=HeyGem Triple GPU Video Generation Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=administrator
WorkingDirectory=/nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts
Environment="PATH=/nvme0n1-disk/nvme01/HeyGem/Heygem_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=/nvme0n1-disk/nvme01/HeyGem/Heygem_env/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable heygem-dual-tts
sudo systemctl start heygem-dual-tts
sudo systemctl status heygem-dual-tts
```

#### 8. Verify Installation

```bash
# Check TTS services
for port in 18182 18183 18184; do
  echo "Testing TTS on port $port..."
  curl -s http://localhost:$port/v1/health || echo "Not ready"
done

# Check GPU services
for port in 8390 8391 8392; do
  echo "Testing GPU on port $port..."
  curl -s http://localhost:$port/easy/query?code=test | head -1
done

# Check Flask API
curl http://localhost:5003/api/info | python3 -m json.tool

# Open web UI
# http://localhost:5003
```

---

## Configuration

### GPU Configuration

Edit `dual_gpu_scheduler.py` line 23-42:

```python
self.gpu_config = {
    0: {
        "port": 8390,       # GPU 0 video port
        "tts_port": 18182,  # GPU 0 TTS port
        "busy": False,
        "current_task": None
    },
    1: {
        "port": 8391,       # GPU 1 video port
        "tts_port": 18183,  # GPU 1 TTS port
        "busy": False,
        "current_task": None
    },
    2: {
        "port": 8392,       # GPU 2 video port
        "tts_port": 18184,  # GPU 2 TTS port
        "busy": False,
        "current_task": None
    }
}
```

### Timeout Configuration

Edit `dual_gpu_scheduler.py` line 245-246:

```python
max_wait = 1800          # Maximum wait time (30 minutes)
check_interval = 5       # Status check interval (5 seconds)
```

### Port Configuration

If ports conflict, modify `docker-compose-dual-tts.yml`:

```yaml
ports:
  - '8390:8383'  # Change 8390 to any free port
  - '18182:8080' # Change 18182 to any free port
```

Then update corresponding port in `dual_gpu_scheduler.py`.

---

## Usage & API

### Web Interface

1. Open browser: `http://localhost:5003`
2. Enter text or drag & drop video
3. Click "Generate Video"
4. Monitor progress in real-time
5. Download result when complete

### API Examples

#### Submit Task

```bash
curl -X POST http://localhost:5003/api/generate \
  -F "text=This is a test video generation" \
  -F "video=@mypath/video.mp4"
```

Response:
```json
{
  "success": true,
  "task_id": "task_1768194928",
  "message": "Task submitted successfully",
  "status_url": "/api/status/task_1768194928"
}
```

#### Check Status

```bash
curl http://localhost:5003/api/status/task_1768194928 | python3 -m json.tool
```

Response:
```json
{
  "status": "processing",
  "progress": 45,
  "gpu_id": 2,
  "timing": {
    "tts_time": 26.5,
    "video_time": null,
    "total_time": null
  }
}
```

#### Monitor Queue

```bash
curl http://localhost:5003/api/queue | python3 -m json.tool
```

---

## Monitoring & Debugging

### Real-time Monitoring

```bash
# Monitor all GPU utilization
watch -n 1 nvidia-smi

# Monitor service logs
sudo journalctl -u heygem-dual-tts -f

# Monitor specific GPU container
docker logs -f heygem-gpu0

# Monitor queue status
watch -n 2 "curl -s http://localhost:5003/api/queue | python3 -m json.tool"
```

### Performance Metrics

```bash
# Check GPU memory usage
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv

# Check active tasks
curl http://localhost:5003/api/queue | jq '.gpus[] | select(.busy==true)'

# Check queue size
curl http://localhost:5003/api/queue | jq '.queue_size'
```

---

## Troubleshooting

### Common Issues & Solutions

See updated [README.md](file:///nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts/README.md) for detailed troubleshooting guide.

**Quick fixes:**
- GPU stuck: `docker restart heygem-gpu[0-2]`
- TTS not responding: `docker restart heygem-tts-dual-[0-2]`
- Service issues: `sudo systemctl restart heygem-dual-tts`
- Port conflicts: Change ports in docker-compose.yml

---

## Best Practices

### Production Deployment

1. **Always use systemd service** for auto-restart
2. **Monitor logs regularly** for early issue detection
3. **Set up log rotation** to prevent disk fill
4. **Use dedicated reference audio** for consistent voice quality
5. **Implement rate limiting** if exposing publicly

### Performance Optimization

1. **Keep GPUs balanced** - avoid overloading specific GPUs
2. **Monitor VRAM usage** - restart if memory leaks detected
3. **Use SSD for data directories** - faster file I/O
4. **Limit concurrent tasks** - max 3 to match GPU count

### Security

1. **Don't expose port 5003 publicly** without authentication
2. **Use reverse proxy** (nginx) with SSL for production
3. **Sanitize user inputs** to prevent injections
4. **Implement file size limits** to prevent DoS

---

## Summary

✅ **6 Containers**: 3 GPU + 3 TTS  
✅ **3x Throughput**: Process 3 videos simultaneously  
✅ **Smart Queuing**: Automatic task distribution  
✅ **Production Ready**: Systemd service + monitoring  
✅ **Well Documented**: Comprehensive troubleshooting guide

**System Status**: 🟢 Ready for production deployment
