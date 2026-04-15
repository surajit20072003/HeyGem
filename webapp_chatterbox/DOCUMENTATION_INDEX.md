# 📚 WebApp Chatterbox - Documentation Index

Welcome to the WebApp Chatterbox documentation! This index will help you find the right documentation for your needs.

---

## 🚀 Getting Started

### **New to the project?** Start here:
1. **[QUICKSTART.md](QUICKSTART.md)** - Quick commands and essential reference
2. **[README.md](README.md)** - Complete setup guide and documentation
3. **[COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md)** - Detailed technical docs

### **Setting up a new server?**
- Run: `./setup_new_server.sh` (automated one-command setup)
- See: [README.md - Installation Guide](README.md#-installation-guide)

---

## 📖 Documentation Files

| File | Purpose | When to Use |
|------|---------|-------------|
| **[README.md](README.md)** | Complete setup & user guide | First-time setup, architecture overview |
| **[QUICKSTART.md](QUICKSTART.md)** | Quick reference & commands | Daily operations, quick lookups |
| **[API_ENDPOINTS.md](API_ENDPOINTS.md)** | API documentation | API integration, development |
| **[SERVICE_COMMANDS.md](SERVICE_COMMANDS.md)** | Service management commands | Operations, troubleshooting |
| **[SYSTEM_LOCATIONS.md](SYSTEM_LOCATIONS.md)** | File locations & structure | Finding files, understanding layout |
| **[COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md)** | Technical deep dive | Development, advanced configuration |
| **[ANALYTICS_AND_DOC.md](ANALYTICS_AND_DOC.md)** | Analytics & monitoring | Performance tracking |

---

## 🎯 Quick Links by Task

### **I want to...**

#### Install on a new server
1. Copy entire `webapp_chatterbox` folder to server
2. Run: `./setup_new_server.sh`
3. Follow prompts
4. Read: [README.md - Installation Guide](README.md#-installation-guide)

#### Start/Stop the service
```bash
# Start
sudo systemctl start heygem-chatterbox

# Stop
sudo systemctl stop heygem-chatterbox

# Full restart
./restart_all.sh
```
📖 See: [QUICKSTART.md](QUICKSTART.md#-essential-commands)

#### Check if everything is running
```bash
curl http://localhost:5004/api/health
```
📖 See: [QUICKSTART.md - Health Checks](QUICKSTART.md#health-checks)

#### Generate a video
```bash
curl -X POST http://localhost:5004/api/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Welcome","language":"english","speaker":"hitesh"}'
```
📖 See: [API_ENDPOINTS.md](API_ENDPOINTS.md)

#### Troubleshoot issues
1. Check logs: `sudo journalctl -u heygem-chatterbox -f`
2. See: [README.md - Troubleshooting](README.md#-troubleshooting)
3. See: [QUICKSTART.md - Troubleshooting](QUICKSTART.md#-troubleshooting)

#### Understand the architecture
📖 See: [README.md - System Architecture](README.md#-system-architecture)

#### Modify or develop
📖 See: [COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md)

---

## 🔧 Essential Files

### Scripts
- **`setup_new_server.sh`** - Automated setup for new servers
- **`start_service.sh`** - Service startup script (called by systemd)
- **`restart_all.sh`** - Full restart (containers + service)

### Service Files
- **`heygem-chatterbox.service`** - Main systemd service
- **`heygem-chatterbox-containers.service`** - Container management service

### Configuration
- **`requirements.txt`** - Python dependencies
- **`vimeo_config.json`** - Vimeo API configuration
- **`task_history.json`** - Task database

### Application
- **`app.py`** - Main Flask application
- **`chatterbox_scheduler.py`** - GPU task scheduler
- **`chatterbox_service.py`** - TTS service
- **`indic_translator.py`** - Language translation
- **`sarvam_tts.py`** - Sarvam.ai TTS integration

---

## 🎓 Learning Path

### Day 1: Setup & Basics
1. Read [QUICKSTART.md](QUICKSTART.md)
2. Install using `setup_new_server.sh`
3. Test API with provided examples
4. Check logs to understand flow

### Day 2: Operations
1. Learn service management from [SERVICE_COMMANDS.md](SERVICE_COMMANDS.md)
2. Practice troubleshooting scenarios
3. Monitor GPU usage with `nvidia-smi`
4. Review task history

### Day 3: Advanced
1. Read [COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md)
2. Understand scheduler logic
3. Explore API endpoints in detail
4. Review code structure

---

## 🆘 Common Issues

| Issue | Quick Fix | Documentation |
|-------|-----------|---------------|
| Service won't start | `sudo journalctl -u heygem-chatterbox -n 50` | [Troubleshooting](README.md#-troubleshooting) |
| TTS not loading | Check GPU memory: `nvidia-smi` | [Troubleshooting](QUICKSTART.md#tts-not-loading) |
| Port conflicts | `./restart_all.sh` | [Troubleshooting](QUICKSTART.md#port-conflicts) |
| Tasks failing | Check container logs: `docker logs heygem-gpu0` | [Troubleshooting](README.md#tasks-failing) |
| API not responding | `curl http://localhost:5004/api/health` | [Health Checks](QUICKSTART.md#health-checks) |

---

## 📞 Support Workflow

1. **Check service status**
   ```bash
   sudo systemctl status heygem-chatterbox
   ```

2. **Check logs**
   ```bash
   sudo journalctl -u heygem-chatterbox -f
   ```

3. **Try restart**
   ```bash
   ./restart_all.sh
   ```

4. **Consult documentation**
   - [README.md - Troubleshooting](README.md#-troubleshooting)
   - [QUICKSTART.md - Troubleshooting](QUICKSTART.md#-troubleshooting)

---

## 🎯 Architecture Quick View

```
User Request (Port 5004)
    ↓
Flask API (app.py)
    ↓
Text Normalization & Translation
    ↓
TTS Generation (Chatterbox/Sarvam)
    ↓
Task Scheduler (chatterbox_scheduler.py)
    ↓
GPU Assignment (0, 1, or 2)
    ↓
Chatterbox TTS Service (20182/20183/20184)
    ↓
Video Generation Container (8390/8391/8392)
    ↓
Final Video → User
```

📖 Full diagram: [README.md - System Architecture](README.md#-system-architecture)

---

## 🌟 Key Features

- ✅ 11 Indian languages + English
- ✅ Voice cloning with Chatterbox-Turbo
- ✅ Multi-GPU processing (3 GPUs)
- ✅ Intelligent queue management
- ✅ Automatic translation (IndicTrans2)
- ✅ Vimeo auto-upload
- ✅ Systemd-based deployment
- ✅ RESTful API
- ✅ Task history tracking

---

## 📊 System Requirements

- **GPUs**: 3 x NVIDIA (24GB+ VRAM)
- **OS**: Ubuntu 20.04+
- **RAM**: 32GB+
- **Storage**: 100GB+
- **Python**: 3.11
- **Docker**: 20.10+

---

## 🚦 Status Indicators

### ✅ Healthy System
```bash
$ curl http://localhost:5004/api/health
{"status":"healthy", ...}

$ sudo systemctl status heygem-chatterbox
● heygem-chatterbox.service - ...
   Active: active (running) ...
```

### ⚠️ Needs Attention
```bash
$ curl http://localhost:5004/api/health
# No response or error
```
👉 Check logs and restart

### ❌ Down
```bash
$ sudo systemctl status heygem-chatterbox
● heygem-chatterbox.service - ...
   Active: failed (Result: exit-code) ...
```
👉 See [Troubleshooting](README.md#-troubleshooting)

---

## 📅 Maintenance

### Daily
- Monitor logs: `sudo journalctl -u heygem-chatterbox -f`
- Check GPU usage: `nvidia-smi`
- Verify health: `curl http://localhost:5004/api/health`

### Weekly
- Review task history: `cat task_history.json | jq`
- Clean old outputs: `rm -f outputs/*.mp4.old`
- Check disk space: `df -h`

### Monthly
- Backup configuration and task history
- Update dependencies if needed
- Review and optimize performance

---

**🎬 You're ready to use WebApp Chatterbox!**

Start with [QUICKSTART.md](QUICKSTART.md) for immediate usage or [README.md](README.md) for complete setup.
