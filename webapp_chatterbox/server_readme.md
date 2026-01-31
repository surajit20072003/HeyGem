# Server Management Commands

Here is the single command to restart everything (Chatterbox TTS + Main API):

```bash
cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox && ./restart_all.sh
```

## Manual Commands (if needed)

### 1. Stop Everything
```bash
pkill -f "chatterbox_service.py"
pkill -f "app.py"
```

### 2. Start Chatterbox TTS (Wait 5-10s after running)
```bash
cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox
nohup ./chatterbox_venv/bin/python chatterbox_service.py --port 20182 --gpu 0 > chatterbox_gpu0.log 2>&1 &
nohup ./chatterbox_venv/bin/python chatterbox_service.py --port 20183 --gpu 1 > chatterbox_gpu1.log 2>&1 &
nohup ./chatterbox_venv/bin/python chatterbox_service.py --port 20184 --gpu 2 > chatterbox_gpu2.log 2>&1 &
```

### 3. Start Main Server
```bash
nohup python3 app.py > app.log 2>&1 &
```

## Check Status
```bash
# Check Processes
ps aux | grep -E "(app.py|chatterbox_service)" | grep -v grep

# Check Health
curl http://localhost:5004/api/health
```
