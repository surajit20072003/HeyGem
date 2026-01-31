# 🎬 WebApp Chatterbox - Complete Setup Guide

## 📋 Overview

**WebApp Chatterbox** is a production-ready video generation system that combines:
- **Multi-language TTS** (11 Indian languages + English)
- **Voice Cloning** using Chatterbox-Turbo
- **Multi-GPU Video Processing** (3 x NVIDIA GPUs)
- **Automated Translation** using IndicTrans2
- **Queue Management** with intelligent GPU scheduling

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│                     systemd Manager                    │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  heygem-chatterbox-containers.service            │ │
│  │  (Manages 3 GPU Docker Containers)              │ │
│  └────────────────┬─────────────────────────────────┘ │
│                   │  depends on                       │
│                   ▼                                   │
│  ┌──────────────────────────────────────────────────┐ │
│  │  heygem-chatterbox.service                       │ │
│  │  (Main Application Service)                      │ │
│  └────────────────┬─────────────────────────────────┘ │
└───────────────────┼──────────────────────────────────┘
                    │
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
   GPU0:8390   GPU1:8391   GPU2:8392
   (lip-sync containers)
        │           │           │
        │           │           │
        ▼           ▼           ▼
   TTS:20182  TTS:20183  TTS:20184
   (voice cloning services)
        │           │           │
        └───────────┴───────────┘
                    │
                    ▼
            Flask API:5004
          (Main REST API)
```

---

## 🎯 Components

### 1. **GPU Containers** (guiji2025/heygem.ai)
- **heygem-gpu0** → Port 8390 → GPU 0
- **heygem-gpu1** → Port 8391 → GPU 1
- **heygem-gpu2** → Port 8392 → GPU 2
- **Purpose**: Wav2Lip video generation
- **Volume**: `/home/administrator/heygem_data/gpu{0,1,2}:/code/data`

### 2. **Chatterbox TTS Services**
- **GPU 0** → Port 20182
- **GPU 1** → Port 20183
- **GPU 2** → Port 20184
- **Purpose**: Voice cloning with Chatterbox-Turbo
- **Model**: Automatic download from HuggingFace

### 3. **Flask API Server**
- **Port**: 5004
- **Purpose**: Main REST API for video generation
- **Features**:
  - Multi-language translation (IndicTrans2)
  - TTS generation (Sarvam.ai integration)
  - Video library management
  - Queue management
  - Vimeo integration

### 4. **Supporting Services**
- **IndicTrans2**: English ↔ 11 Indian languages
- **Sarvam.ai**: TTS for Indian languages
- **Vimeo API**: Auto-upload completed videos

---

## 📦 Dependencies

### System Requirements
- **OS**: Ubuntu 20.04+ / Linux
- **GPU**: 3 x NVIDIA GPUs (24GB+ VRAM recommended)
- **RAM**: 32GB+
- **Storage**: 100GB+ free space
- **CUDA**: 11.8+
- **Docker**: 20.10+

### Python Environment
- **Python**: 3.11 (via pyenv)
- **Virtual Environment**: `chatterbox_venv`

### Key Python Packages
```
chatterbox-tts      # Voice cloning
flask               # Web framework
flask-cors          # CORS support
requests            # HTTP client
torch               # PyTorch
torchaudio          # Audio processing
```

---

## 🚀 Installation Guide

### Prerequisites Check
```bash
# Check GPU
nvidia-smi

# Check Docker
docker --version

# Check Python
python3 --version
```

### Step 1: Clone & Setup Directory
```bash
# Create base folder
mkdir -p /nvme0n1-disk/nvme01/HeyGem
cd /nvme0n1-disk/nvme01/HeyGem

# Clone your repository (or copy files)
# git clone <your-repo> webapp_chatterbox
cd webapp_chatterbox
```

### Step 2: Install Python Environment
```bash
# Install pyenv (if not installed)
curl https://pyenv.run | bash

# Add to ~/.bashrc
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"

# Reload
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.0
pyenv local 3.11.0

# Create virtual environment
python -m venv chatterbox_venv
source chatterbox_venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Setup GPU Containers
```bash
# Create data directories
sudo mkdir -p /home/administrator/heygem_data/gpu{0,1,2}
sudo chown -R $USER:$USER /home/administrator/heygem_data

# Pull Docker image
docker pull guiji2025/heygem.ai

# Create containers
docker create --name heygem-gpu0 \
    --gpus '"device=0"' \
    -p 8390:8383 \
    -v /home/administrator/heygem_data/gpu0:/code/data \
    guiji2025/heygem.ai \
    python /code/app_local.py --port 8383

docker create --name heygem-gpu1 \
    --gpus '"device=1"' \
    -p 8391:8383 \
    -v /home/administrator/heygem_data/gpu1:/code/data \
    guiji2025/heygem.ai \
    python /code/app_local.py --port 8383

docker create --name heygem-gpu2 \
    --gpus '"device=2"' \
    -p 8392:8383 \
    -v /home/administrator/heygem_data/gpu2:/code/data \
    guiji2025/heygem.ai \
    python /code/app_local.py --port 8383
```

### Step 4: Setup Environment Variables
```bash
# Add to ~/.bashrc or service file
export SARVAM_API_KEY="your_sarvam_api_key_here"
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
```

### Step 5: Install System Services
```bash
cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox

# Make scripts executable
chmod +x start_service.sh restart_all.sh

# Copy service files
sudo cp heygem-chatterbox-containers.service /etc/systemd/system/
sudo cp heygem-chatterbox.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable heygem-chatterbox-containers
sudo systemctl enable heygem-chatterbox
```

### Step 6: Create Required Files
```bash
# Create default video (place your default.mp4)
# cp /path/to/your/default.mp4 ./default.mp4

# Create reference audio for voice cloning
# cp /path/to/reference.wav ./reference_audio.wav

# Create necessary directories
mkdir -p uploads outputs temp library/videos library/audios
```

### Step 7: Start Services
```bash
# Start GPU containers first
sudo systemctl start heygem-chatterbox-containers

# Wait for containers to be ready (15-20 seconds)
sleep 20

# Start main service
sudo systemctl start heygem-chatterbox

# Check status
sudo systemctl status heygem-chatterbox
```

---

## 🔧 Quick Start (One-Command)

Save this as `setup.sh` and run:

```bash
#!/bin/bash
# Complete setup script for new server

set -e

echo "🚀 Starting WebApp Chatterbox Setup..."

# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv ffmpeg git curl

# Setup directories
mkdir -p /home/administrator/heygem_data/gpu{0,1,2}
mkdir -p uploads outputs temp library/videos library/audios

# Setup Python environment
python3 -m venv chatterbox_venv
source chatterbox_venv/bin/activate
pip install --upgrade pip
pip install chatterbox-tts flask flask-cors requests torch torchaudio

# Setup services
chmod +x start_service.sh restart_all.sh
sudo cp heygem-chatterbox-containers.service /etc/systemd/system/
sudo cp heygem-chatterbox.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable heygem-chatterbox-containers heygem-chatterbox

echo "✅ Setup complete! Now start containers and service."
```

---

## 📡 API Endpoints

### Health Check
```bash
GET http://localhost:5004/api/health
```

### Generate Video
```bash
POST http://localhost:5004/api/generate
Content-Type: application/json

{
  "text": "Your input text",
  "language": "hindi",
  "speaker": "hitesh",
  "video_file": "optional_custom_video.mp4"
}
```

### Check Task Status
```bash
GET http://localhost:5004/api/status/{task_id}
```

### Download Video
```bash
GET http://localhost:5004/api/download/{task_id}
```

### View History
```bash
GET http://localhost:5004/api/history
```

---

## 🔄 Service Management

### Start Service
```bash
sudo systemctl start heygem-chatterbox
```

### Stop Service
```bash
sudo systemctl stop heygem-chatterbox
```

### Restart (Full - Containers + Service)
```bash
cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox
./restart_all.sh
```

### Restart (Service Only)
```bash
sudo systemctl restart heygem-chatterbox
```

### Check Status
```bash
# Service status
sudo systemctl status heygem-chatterbox

# Live logs
sudo journalctl -u heygem-chatterbox -f

# Check all ports
netstat -tlnp | grep -E ':(5004|8390|8391|8392|20182|20183|20184)'
```

### Health Verification
```bash
# Quick health check
curl http://localhost:5004/api/health

# TTS services
curl http://localhost:20182/health
curl http://localhost:20183/health
curl http://localhost:20184/health

# GPU containers (basic connectivity)
nc -zv localhost 8390
nc -zv localhost 8391
nc -zv localhost 8392
```

---

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u heygem-chatterbox -n 100

# Check container service
sudo systemctl status heygem-chatterbox-containers

# Restart containers
sudo docker restart heygem-gpu0 heygem-gpu1 heygem-gpu2
```

### TTS Services Not Loading
```bash
# Check TTS logs
tail -f chatterbox_gpu0.log
tail -f chatterbox_gpu1.log
tail -f chatterbox_gpu2.log

# Check GPU memory
nvidia-smi

# Free GPU memory if needed
sudo systemctl restart heygem-chatterbox
```

### Tasks Failing
```bash
# Check task history
cat task_history.json | jq .

# Check GPU container logs
docker logs heygem-gpu0 --tail 50

# Verify file permissions
ls -lah /home/administrator/heygem_data/gpu0/
```

### Port Conflicts
```bash
# Find processes using ports
lsof -i :5004
lsof -i :20182

# Kill conflicting processes
sudo pkill -f "chatterbox_service.py"
sudo pkill -f "webapp_chatterbox.*app.py"
```

---

## 📊 Monitoring

### Real-time Monitoring
```bash
# Service logs
sudo journalctl -u heygem-chatterbox -f

# GPU usage
watch -n 1 nvidia-smi

# Task queue
curl -s http://localhost:5004/api/status | jq .
```

### Performance Metrics
- **TTS Generation**: ~5-15 seconds per minute of audio
- **Video Processing**: ~30-60 seconds per video
- **Concurrent Tasks**: Up to 3 (one per GPU)
- **Queue Management**: Automatic with FIFO

---

## 🔐 Security Notes

### API Key Management
Store sensitive keys in environment variables:
```bash
# In /etc/systemd/system/heygem-chatterbox.service
Environment=SARVAM_API_KEY=your_api_key_here
```

### File Permissions
```bash
# Ensure proper ownership
sudo chown -R administrator:administrator /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox
sudo chown -R administrator:administrator /home/administrator/heygem_data
```

### Network Security
- Bind to localhost only in production
- Use reverse proxy (nginx/apache) for external access
- Enable HTTPS for production deployments

---

## 📝 File Structure

```
webapp_chatterbox/
├── app.py                          # Main Flask application
├── chatterbox_scheduler.py         # GPU task scheduler
├── chatterbox_service.py           # TTS service
├── indic_translator.py             # Language translation
├── sarvam_tts.py                   # Sarvam.ai TTS integration
├── text_normalization.py           # LaTeX to speech
├── library_manager.py              # Video/audio library
├── vimeo_api.py                    # Vimeo upload
├── start_service.sh               # Startup script
├── restart_all.sh                  # Full restart script
├── heygem-chatterbox.service       # Main systemd service
├── heygem-chatterbox-containers.service  # Container service
├── requirements.txt                # Python dependencies
├── default.mp4                     # Default video template
├── reference_audio.wav             # Voice cloning reference
├── task_history.json              # Task history database
├── uploads/                        # User uploads
├── outputs/                        # Generated videos
├── temp/                          # Temporary files
├── library/                       # Video/audio library
│   ├── videos/
│   └── audios/
└── chatterbox_venv/               # Python virtual environment
```

---

## 🎓 Supported Languages

### Indian Languages (11)
1. Hindi (हिन्दी)
2. Bengali (বাংলা)
3. Tamil (தமிழ்)
4. Telugu (తెలుగు)
5. Marathi (मराठी)
6. Malayalam (മലയാളം)
7. Kannada (ಕನ್ನಡ)
8. Gujarati (ગુજરાતી)
9. Punjabi (ਪੰਜਾਬੀ)
10. Odia (ଓଡ଼ିଆ)
11. Assamese (অসমীয়া)

### English
- Automatic translation to/from English

---

## 🤝 Contributing

### Development Setup
```bash
# Activate virtual environment
source chatterbox_venv/bin/activate

# Install dev dependencies
pip install pytest black flake8

# Run tests
pytest
```

### Code Style
- Follow PEP 8
- Use Black for formatting
- Maximum line length: 100 characters

---

## 📄 License

[Your License Here]

---

## 🆘 Support

For issues and questions:
- Check logs: `sudo journalctl -u heygem-chatterbox -f`
- Review documentation files in the repo
- Check troubleshooting section above

---

## 🎉 Quick Test

After setup, test the system:

```bash
# 1. Check health
curl http://localhost:5004/api/health

# 2. Generate a test video
curl -X POST http://localhost:5004/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to our service",
    "language": "english",
    "speaker": "hitesh"
  }' | jq .

# 3. Check status (use task_id from above)
curl http://localhost:5004/api/status/task_xxx | jq .

# 4. Download when complete
curl -O http://localhost:5004/api/download/task_xxx
```

---

**🎬 Ready to create amazing multilingual videos with voice cloning!**
