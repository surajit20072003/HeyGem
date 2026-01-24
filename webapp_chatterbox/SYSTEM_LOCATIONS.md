# System Locations Map - Triple GPU Setup

## 📍 Complete Location Guide

### 1. Docker Containers (Running Processes)

**Location**: Running in Docker daemon memory
**View**: `docker ps` or `docker container ls`

```bash
# All containers running in Docker
CONTAINER NAME          STATUS    PORTS
heygem-gpu0            Up        0.0.0.0:8390->8383/tcp
heygem-gpu1            Up        0.0.0.0:8391->8383/tcp
heygem-gpu2            Up        0.0.0.0:8392->8383/tcp
heygem-tts-dual-0      Up        0.0.0.0:18182->8080/tcp
heygem-tts-dual-1      Up        0.0.0.0:18183->8080/tcp
heygem-tts-dual-2      Up        0.0.0.0:18184->8080/tcp
```

**Actual Process Location**:
```bash
# Check where containers are running
docker inspect heygem-gpu0 | jq '.[0].State'
# Shows: Running in /var/lib/docker/containers/
```

---

### 2. Docker Images (Base Templates)

**Location**: `/var/lib/docker/`
**Storage Driver**: Usually overlay2

```bash
# Image storage location
/var/lib/docker/
├── image/
│   └── overlay2/           # Image layers
├── overlay2/               # Container filesystems
└── containers/             # Container configs

# View images
docker images
```

**Image Details**:
```
REPOSITORY                        SIZE      LOCATION
guiji2025/heygem.ai              ~25GB     /var/lib/docker/image/overlay2/
guiji2025/fish-speech-ziming     ~15GB     /var/lib/docker/image/overlay2/
```

---

### 3. Project Code (Your Application)

**Main Location**: `/nvme0n1-disk/nvme01/HeyGem/`

```
/nvme0n1-disk/nvme01/HeyGem/
├── docker-compose-dual-tts.yml        # Container orchestration
├── webapp_dual_tts/                   # Main application
│   ├── app.py                         # Flask server
│   ├── dual_gpu_scheduler.py          # GPU scheduler
│   ├── text_normalization.py          # Text processing
│   ├── static/index.html              # Web UI
│   ├── uploads/                       # User uploads
│   ├── outputs/                       # Generated videos
│   ├── temp/                          # Temporary files
│   └── requirements.txt               # Python deps
├── README.md
└── Heygem_env/                        # Python virtual environment
```

---

### 4. Data Directories (Shared Volumes)

**Actual Location**: `/nvme0n1-disk/nvme01/heygem_data/`  
**Symlink**: `/home/administrator/heygem_data → /nvme0n1-disk/nvme01/heygem_data`

> **Note**: Docker compose uses `/home/administrator/heygem_data/` which is a **symbolic link** pointing to the actual data on NVME drive. This keeps data on fast storage while maintaining compatibility.

```
/nvme0n1-disk/nvme01/heygem_data/      # Real location (NVME drive)
├── gpu0/                               # GPU 0 shared folder
│   ├── default.mp4                     # Default video (73MB)
│   ├── temp/                           # Temp processing files
│   ├── result/                         # Output videos
│   ├── log/                            # Processing logs
│   └── tts_task_*.wav                  # TTS audio files
│
├── gpu1/                               # GPU 1 shared folder
│   └── (same structure as gpu0)
│
├── gpu2/                               # GPU 2 shared folder
│   └── (same structure as gpu0)
│
├── tts0/                               # TTS 0 data
│   └── reference/                      # Reference audio files
│       └── ref_task_*.wav
│
├── tts1/                               # TTS 1 data
│   └── reference/
│
└── tts2/                               # TTS 2 data
    └── reference/
```

**Volume Mapping** (Host → Container):
```
Host Path (via symlink)                      →  Container Path
/home/administrator/heygem_data/gpu0    →  /code/data  (in heygem-gpu0)
  ↓ (actually points to)
/nvme0n1-disk/nvme01/heygem_data/gpu0

/home/administrator/heygem_data/gpu1    →  /code/data  (in heygem-gpu1)
/home/administrator/heygem_data/gpu2    →  /code/data  (in heygem-gpu2)
/home/administrator/heygem_data/tts0    →  /code/data  (in heygem-tts-dual-0)
/home/administrator/heygem_data/tts1    →  /code/data  (in heygem-tts-dual-1)
/home/administrator/heygem_data/tts2    →  /code/data  (in heygem-tts-dual-2)
```

---

### 5. Container Internal Structure

**GPU Container** (heygem-gpu0/1/2):
```
Inside Container                       External Access
/code/                                 [Read-only from image]
├── app_local.py                       Main GPU processing app
├── models/                            AI models
└── data/                    →         /home/administrator/heygem_data/gpu[0-2]/
    ├── default.mp4
    ├── temp/
    └── result/
```

**TTS Container** (heygem-tts-dual-0/1/2):
```
Inside Container                       External Access
/code/                                 [Read-only from image]
├── tools/
│   └── api_server.py                  TTS API server
└── data/                    →         /home/administrator/heygem_data/tts[0-2]/
    └── reference/
```

---

### 6. Systemd Service

**Service File**: `/etc/systemd/system/heygem-dual-tts.service`

```bash
# Service configuration
[Unit]
Description=HeyGem Triple GPU Video Generation Service

[Service]
WorkingDirectory=/nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts
ExecStart=/nvme0n1-disk/nvme01/HeyGem/Heygem_env/bin/python3 app.py
```

**Service Management**:
```bash
sudo systemctl status heygem-dual-tts
sudo systemctl start heygem-dual-tts
sudo systemctl stop heygem-dual-tts
sudo systemctl restart heygem-dual-tts
```

---

### 7. Logs & Monitoring

**Service Logs**:
```bash
# Systemd service logs
sudo journalctl -u heygem-dual-tts -f
# Location: /var/log/journal/
```

**Docker Logs**:
```bash
# Container logs (stored in Docker)
docker logs heygem-gpu0
docker logs heygem-tts-dual-0
# Location: /var/lib/docker/containers/[container-id]/[container-id]-json.log
```

**Application Logs**:
```bash
# GPU container logs
/home/administrator/heygem_data/gpu0/log/
/home/administrator/heygem_data/gpu1/log/
/home/administrator/heygem_data/gpu2/log/
```

---

### 8. Network & Ports

**Network Type**: Bridge network `heygem_network`

```bash
# Check network
docker network inspect heygem_network

# Network location
/var/lib/docker/network/files/local-kv.db
```

**Port Bindings**:
```
External Port    →  Internal Port    Container
8390             →  8383              heygem-gpu0
8391             →  8383              heygem-gpu1
8392             →  8383              heygem-gpu2
18182            →  8080              heygem-tts-dual-0
18183            →  8080              heygem-tts-dual-1
18184            →  8080              heygem-tts-dual-2
5003             →  5003              Flask API (host)
```

---

### 9. Docker Compose File

**Location**: `/nvme0n1-disk/nvme01/HeyGem/docker-compose-dual-tts.yml`

This file defines all 6 containers and their configuration.

---

### 10. Python Environment

**Virtual Environment**: `/nvme0n1-disk/nvme01/HeyGem/Heygem_env/`

```
Heygem_env/
├── bin/
│   ├── python3         # Python interpreter
│   ├── pip            # Package manager
│   └── flask          # Flask executable
├── lib/
│   └── python3.*/
│       └── site-packages/   # Installed packages
│           ├── flask/
│           ├── requests/
│           └── ...
```

---

## 📊 Quick Access Commands

```bash
# View all container locations
docker inspect heygem-gpu0 | jq '.[0].GraphDriver'

# Check disk usage
du -sh /home/administrator/heygem_data/*
du -sh /var/lib/docker/

# Find all project files
find /nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts -type f -name "*.py"

# Check data directories
ls -lh ~/heygem_data/gpu*/

# Monitor real-time
watch -n 2 "docker stats --no-stream"
```

---

## 🗺️ Visual Map

```
┌─────────────────────────────────────────────────────────────┐
│                    Physical Server                          │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │              Docker Daemon                             ││
│  │              (/var/lib/docker/)                        ││
│  │                                                        ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ ││
│  │  │  heygem-gpu0 │  │  heygem-gpu1 │  │ heygem-gpu2 │ ││
│  │  │  (Container) │  │  (Container) │  │ (Container) │ ││
│  │  │              │  │              │  │             │ ││
│  │  │  /code/data ─┼──┼─────────────┼──┼─Mounted to  │ ││
│  │  └──────────────┘  └──────────────┘  └─────────────┘ ││
│  │         │                 │                 │         ││
│  └─────────┼─────────────────┼─────────────────┼─────────┘│
│            │                 │                 │          │
│            ▼                 ▼                 ▼          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  /home/administrator/heygem_data/                    │ │
│  │  ├── gpu0/  ├── gpu1/  ├── gpu2/                    │ │
│  │  ├── tts0/  ├── tts1/  ├── tts2/                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  /nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts/        │ │
│  │  (Flask API runs here - NOT in container)            │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Summary

| Component | Docker Path | Actual Location | Size |
|-----------|-------------|-----------------|------|
| **Docker Images** | - | `/var/lib/docker/image/` | ~40GB |
| **Containers** | - | `/var/lib/docker/containers/` | Running |
| **Code** | - | `/nvme0n1-disk/nvme01/HeyGem/` | ~100MB |
| **Data Volumes** | `/home/administrator/heygem_data/` | `/nvme0n1-disk/nvme01/heygem_data/` ⭐ | ~150GB |
| **Flask API** | - | `/nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts/` | ~10MB |
| **Service** | - | `/etc/systemd/system/heygem-dual-tts.service` | ~1KB |
| **Logs** | - | `/var/log/journal/` + Docker logs | Varies |

⭐ **Note**: `/home/administrator/heygem_data/` is a **symlink** to `/nvme0n1-disk/nvme01/heygem_data/`

All locations mapped! 🗺️
