# HeyGem Chatterbox Service Commands

## Service Management

### Start service
```bash
sudo systemctl start heygem-chatterbox
```

### Stop service  
```bash
sudo systemctl stop heygem-chatterbox
```

### Restart service
```bash
sudo systemctl restart heygem-chatterbox
```

### Check status
```bash
sudo systemctl status heygem-chatterbox
```

### Enable auto-start on boot
```bash
sudo systemctl enable heygem-chatterbox
```

### Disable auto-start
```bash
sudo systemctl disable heygem-chatterbox
```

## Logs

### View real-time logs
```bash
sudo journalctl -u heygem-chatterbox -f
```

### View recent logs
```bash
sudo journalctl -u heygem-chatterbox -n 100
```

### Check if service is active
```bash
systemctl status heygem-chatterbox | grep "Active:"
```

## Quick Status Check

### Check all HeyGem services
```bash
systemctl list-units --type=service | grep heygem
```

### View recent task submissions
```bash
sudo journalctl -u heygem-chatterbox --no-pager | grep "New Task" | tail -n 15
```

## API Endpoints

- **Web Interface:** http://localhost:5004
- **API Info:** http://localhost:5004/api/info
- **Queue Status:** http://localhost:5004/api/queue
- **Health Check:** http://localhost:5004/api/health

## Chatterbox TTS Services

- **TTS 0 (GPU 0):** http://localhost:20182
- **TTS 1 (GPU 1):** http://localhost:20183
- **TTS 2 (GPU 2):** http://localhost:20184

## Troubleshooting

### If service fails to start
```bash
# Check logs for errors
sudo journalctl -u heygem-chatterbox -n 50

# Verify virtual environment
ls -la /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox/chatterbox_venv/

# Test startup script manually
cd /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox
./start_service.sh
```

### Reload systemd after changes
```bash
sudo systemctl daemon-reload
sudo systemctl restart heygem-chatterbox
```
