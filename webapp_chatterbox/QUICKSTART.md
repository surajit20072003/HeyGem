# 🚀 WebApp Chatterbox - Quick Reference Guide

## ⚡ One-Command Setup (New Server)

```bash
cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox
./setup_new_server.sh
```

This will automatically:
- ✅ Install all dependencies
- ✅ Configure Python environment
- ✅ Setup Docker containers
- ✅ Configure systemd services
- ✅ Start everything

---

## 🎯 Essential Commands

### Service Management

```bash
# Start
sudo systemctl start heygem-chatterbox

# Stop
sudo systemctl stop heygem-chatterbox

# Restart (service only)
sudo systemctl restart heygem-chatterbox

# Full restart (containers + service)
cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox && ./restart_all.sh

# Status
sudo systemctl status heygem-chatterbox

# Logs (live)
sudo journalctl -u heygem-chatterbox -f
```

### Health Checks

```bash
# API
curl http://localhost:5004/api/health

# TTS Services
curl http://localhost:20182/health  # GPU 0
curl http://localhost:20183/health  # GPU 1
curl http://localhost:20184/health  # GPU 2

# All ports
netstat -tlnp | grep -E ':(5004|8390|8391|8392|20182|20183|20184)'
```

### Quick Test

```bash
# Generate test video
curl -X POST http://localhost:5004/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to our service",
    "language": "english",
    "speaker": "hitesh"
  }' | jq .

# Check status (use task_id from response)
curl http://localhost:5004/api/status/task_xxx | jq .
```

---

## 🔧 Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u heygem-chatterbox -n 100 --no-pager

# Restart containers
sudo docker restart heygem-gpu0 heygem-gpu1 heygem-gpu2

# Full restart
./restart_all.sh
```

### TTS Not Loading
```bash
# Check TTS logs
tail -f chatterbox_gpu0.log

# Check GPU memory
nvidia-smi

# Restart service
sudo systemctl restart heygem-chatterbox
```

### Port Conflicts
```bash
# Find conflicts
lsof -i :5004
lsof -i :20182

# Kill manual processes
sudo pkill -f "chatterbox_service.py"
sudo pkill -f "app.py"

# Restart clean
./restart_all.sh
```

---

## 📊 System Overview

### Ports
| Service | Port | Purpose |
|---------|------|---------|
| Flask API | 5004 | Main REST API |
| TTS GPU 0 | 20182 | Voice cloning |
| TTS GPU 1 | 20183 | Voice cloning |
| TTS GPU 2 | 20184 | Voice cloning |
| Container GPU 0 | 8390 | Video processing |
| Container GPU 1 | 8391 | Video processing |
| Container GPU 2 | 8392 | Video processing |

### File Locations
```
/nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox/     # Main directory
├── app.py                                          # Flask app
├── chatterbox_scheduler.py                         # Scheduler
├── start_service.sh                               # Startup script
├── restart_all.sh                                  # Restart script
├── task_history.json                              # Task database
├── outputs/                                        # Generated videos
└── uploads/                                        # User uploads

/home/administrator/heygem_data/                    # GPU shared data
├── gpu0/                                           # GPU 0 files
├── gpu1/                                           # GPU 1 files
└── gpu2/                                           # GPU 2 files

/etc/systemd/system/                                # Services
├── heygem-chatterbox.service                       # Main service
└── heygem-chatterbox-containers.service            # Containers
```

### Logs
```bash
# Service logs
sudo journalctl -u heygem-chatterbox -f

# TTS logs
tail -f chatterbox_gpu0.log
tail -f chatterbox_gpu1.log
tail -f chatterbox_gpu2.log

# Container logs
docker logs heygem-gpu0 --tail 50
docker logs heygem-gpu1 --tail 50
docker logs heygem-gpu2 --tail 50
```

---

## 🌎 Supported Languages

Hindi, Bengali, Tamil, Telugu, Marathi, Malayalam, Kannada, Gujarati, Punjabi, Odia, Assamese, English

---

## 📞 Quick Support

```bash
# System status
sudo systemctl status heygem-chatterbox --no-pager

# GPU status
nvidia-smi

# Disk space
df -h

# Memory
free -h

# Processes
ps aux | grep -E "chatterbox|app.py"
```

---

## 🎬 API Examples

### Generate Video (English)
```bash
curl -X POST http://localhost:5004/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test video",
    "language": "english",
    "speaker": "hitesh"
  }'
```

### Generate Video (Hindi)
```bash
curl -X POST http://localhost:5004/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to our platform",
    "language": "hindi",
    "speaker": "hitesh"
  }'
```

### Check History
```bash
curl http://localhost:5004/api/history | jq .
```

---

## 🔐 Environment Variables

Set in service file: `/etc/systemd/system/heygem-chatterbox.service`

```ini
Environment=SARVAM_API_KEY=your_api_key_here
Environment=PYTHONUNBUFFERED=1
Environment=PYENV_ROOT=/home/administrator/.pyenv
```

After changing, reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart heygem-chatterbox
```

---

## 💡 Pro Tips

1. **Monitor GPU usage**: `watch -n 1 nvidia-smi`
2. **Keep logs clean**: Rotate logs regularly
3. **Backup task history**: `cp task_history.json task_history.json.backup`
4. **Test after restart**: Always run health check
5. **Check disk space**: Videos can accumulate quickly

---

**For full documentation, see [README.md](README.md)**
