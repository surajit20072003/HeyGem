# HeyGem.ai - Second Server Setup Guide

## 📋 Overview
Ye guide aapko 2nd server pe complete HeyGem.ai setup karne me help karega. Is project me **4 Docker containers** use ho rahe hain - 3 GPU containers aur 1 TTS (Text-to-Speech) container.

---

## 🐋 Docker Containers Summary

### Current Running Containers
```
CONTAINER NAME       IMAGE                              PORT MAPPING        GPU ASSIGNED
heygem-gpu0         guiji2025/heygem.ai                8390:8383          GPU 0
heygem-gpu1         guiji2025/heygem.ai                8391:8383          GPU 1
heygem-gpu2         guiji2025/heygem.ai                8392:8383          GPU 2
heygem-tts-new      guiji2025/fish-speech-ziming       18181:8080         GPU 0
```

### Docker Images Required
```bash
# Main Images
guiji2025/heygem.ai:latest              # Video generation
guiji2025/fish-speech-ziming:latest     # TTS (Voice cloning)
```

---

## 🔧 Prerequisites (2nd Server pe install karna hai)

### 1. System Requirements
```bash
# Check GPU availability
nvidia-smi

# Required:
# - NVIDIA GPUs (recommended: 3x RTX A5000 or similar)
# - Minimum 24GB VRAM per GPU
# - Ubuntu/Linux OS
# - 100GB+ free disk space
```

### 2. Install Docker
```bash
# Docker install karo
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# User ko docker group me add karo
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
```

### 3. Install NVIDIA Container Toolkit
```bash
# Add NVIDIA Docker repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install nvidia-docker2
sudo apt-get update
sudo apt-get install -y nvidia-docker2

# Restart Docker
sudo systemctl restart docker

# Test GPU access in Docker
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 4. Install Docker Compose
```bash
# Docker Compose install karo
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

---

## 📦 Setup Steps

### Step 1: Create Project Directory
```bash
# Project directory banao
mkdir -p ~/HeyGem
cd ~/HeyGem

# Data directories banao (docker volumes ke liye)
mkdir -p ~/heygem_data/gpu0
mkdir -p ~/heygem_data/gpu1
mkdir -p ~/heygem_data/gpu2
mkdir -p ~/heygem_data/tts
```

### Step 2: Pull Docker Images
```bash
# Video generation image pull karo (approx 20GB)
docker pull guiji2025/heygem.ai:latest

# TTS image pull karo (approx 15GB)
docker pull guiji2025/fish-speech-ziming:latest

# Verify images
docker images
```

### Step 3: Create Docker Compose File

**File: `~/HeyGem/docker-compose-setup.yml`**

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

  # GPU 2 - Video Generation
  heygem-gpu2:
    image: guiji2025/heygem.ai
    container_name: heygem-gpu2
    restart: always
    runtime: nvidia
    privileged: true
    environment:
      - CUDA_VISIBLE_DEVICES=2
      - PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['2']
              capabilities: [gpu]
    shm_size: '8g'
    ports:
      - '8392:8383'
    volumes:
      - ~/heygem_data/gpu2:/code/data
    command: python /code/app_local.py
    networks:
      - heygem_network

  # TTS Service (Voice Cloning)
  heygem-tts:
    image: guiji2025/fish-speech-ziming
    container_name: heygem-tts-new
    restart: always
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
      - NVIDIA_DRIVER_CAPABILITIES=compute,graphics,utility,video,display
    ports:
      - '18181:8080'
    volumes:
      - ~/heygem_data/tts:/code/data
    command: /bin/bash -c "/opt/conda/envs/python310/bin/python3 tools/api_server.py --listen 0.0.0.0:8080"
    networks:
      - heygem_network
```

### Step 4: Start Docker Containers
```bash
cd ~/HeyGem

# Containers start karo
docker-compose -f docker-compose-setup.yml up -d

# Status check karo
docker ps

# Logs check karo (koi error hai to)
docker logs heygem-gpu0
docker logs heygem-gpu1
docker logs heygem-gpu2
docker logs heygem-tts-new
```

---

## 🐍 Python Dependencies (Host Machine pe)

Agar aapko host machine se API calls karni hain, to ye Python packages install karo:

### requirements.txt (webapp_multi_video ke liye)
```txt
Flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
psutil==5.9.0
```

### Installation Commands
```bash
# Python virtual environment banao (recommended)
python3 -m venv venv
source venv/bin/activate

# Dependencies install karo
pip install Flask==3.0.0
pip install flask-cors==4.0.0
pip install requests==2.31.0
pip install psutil==5.9.0
```

---

## 🧪 Testing Setup

### Test GPU Containers
```bash
# Test GPU 0
curl -X POST http://localhost:8390/health

# Test GPU 1
curl -X POST http://localhost:8391/health

# Test GPU 2
curl -X POST http://localhost:8392/health

# Test TTS
curl -X POST http://localhost:18181/health
```

### Test Video Generation (Python script)
```python
import requests

# GPU 0 pe video generate karo
url = "http://localhost:8390/generate"
data = {
    "input_video": "/code/data/input.mp4",
    "input_audio": "/code/data/audio.mp3"
}

response = requests.post(url, json=data)
print(response.json())
```

---

## 📊 GPU Memory & Performance

### Current Configuration
- **Each GPU**: 2 parallel tasks (totL 6 parallel videos)
- **VRAM per task**: ~9GB
- **Shared memory**: 8GB per container
- **Memory split**: max_split_size_mb=512

### Monitor GPU Usage
```bash
# Real-time GPU monitoring
watch -n 1 nvidia-smi

# Container resource usage
docker stats
```

---

## 🔥 Common Commands

### Start/Stop Containers
```bash
# Start all
docker-compose -f docker-compose-setup.yml up -d

# Stop all
docker-compose -f docker-compose-setup.yml down

# Restart specific container
docker restart heygem-gpu0

# View logs
docker logs -f heygem-gpu0
```

### Update Images
```bash
# Pull latest images
docker pull guiji2025/heygem.ai:latest
docker pull guiji2025/fish-speech-ziming:latest

# Recreate containers
docker-compose -f docker-compose-setup.yml up -d --force-recreate
```

### Clean Up
```bash
# Stop and remove containers
docker-compose -f docker-compose-setup.yml down

# Remove images (optional)
docker rmi guiji2025/heygem.ai
docker rmi guiji2025/fish-speech-ziming

# Remove volumes (optional - ye data delete karega!)
docker volume prune
```

---

## 📝 Important Notes

### Port Mapping
- **8390**: GPU 0 API (heygem-gpu0)
- **8391**: GPU 1 API (heygem-gpu1)
- **8392**: GPU 2 API (heygem-gpu2)
- **18181**: TTS API (voice cloning)

### Volume Mapping
- `~/heygem_data/gpu0` → Container `/code/data` (GPU 0)
- `~/heygem_data/gpu1` → Container `/code/data` (GPU 1)
- `~/heygem_data/gpu2` → Container `/code/data` (GPU 2)
- `~/heygem_data/tts` → Container `/code/data` (TTS)

### GPU Assignment
- **GPU 0**: heygem-gpu0 + heygem-tts (TTS bhi GPU 0 use karta hai)
- **GPU 1**: heygem-gpu1
- **GPU 2**: heygem-gpu2

---

## 🚀 Quick Start Commands (Copy-Paste)

```bash
# Complete setup in one go
sudo apt-get update
sudo apt-get install -y curl

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install NVIDIA Docker
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create directories
mkdir -p ~/HeyGem/{gpu0,gpu1,gpu2,tts}
mkdir -p ~/heygem_data/{gpu0,gpu1,gpu2,tts}
cd ~/HeyGem

# Pull images
docker pull guiji2025/heygem.ai:latest
docker pull guiji2025/fish-speech-ziming:latest

# Copy docker-compose file from above and save as docker-compose-setup.yml
# Then start containers
docker-compose -f docker-compose-setup.yml up -d

# Check status
docker ps
nvidia-smi
```

---

## ✅ Final Checklist

- [ ] Docker installed
- [ ] NVIDIA Container Toolkit installed
- [ ] Docker Compose installed
- [ ] Images pulled (`guiji2025/heygem.ai` and `guiji2025/fish-speech-ziming`)
- [ ] Data directories created
- [ ] docker-compose-setup.yml created
- [ ] Containers started successfully
- [ ] All 4 containers running (`docker ps` shows all)
- [ ] GPUs visible in containers (`docker exec heygem-gpu0 nvidia-smi`)
- [ ] APIs responding (health check endpoints)

---

## 🆘 Troubleshooting

### Issue: Container fails to start
```bash
# Check logs
docker logs heygem-gpu0

# Check GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Issue: Port already in use
```bash
# Find process using port
sudo lsof -i :8390

# Kill process
sudo kill -9 <PID>
```

### Issue: Out of memory
```bash
# Check GPU memory
nvidia-smi

# Reduce parallel tasks
# Modify PYTORCH_CUDA_ALLOC_CONF or reduce concurrent videos
```

---

**Setup complete! Ab aap dusre server pe bhi same setup run kar sakte ho! 🎉**
