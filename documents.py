Controls:

Start: sudo systemctl start heygem-single
Stop: sudo systemctl stop heygem-single
Status: sudo systemctl status heygem-single

sudo systemctl restart heygem-chunked heygem-single



# Start service
sudo systemctl start heygem-dual-tts

# Stop service  
sudo systemctl stop heygem-dual-tts

# Restart service
sudo systemctl restart heygem-dual-tts

# Check status
sudo systemctl status heygem-dual-tts

# View logs
sudo journalctl -u heygem-dual-tts -f