#!/bin/bash
# Restart HeyGem Chatterbox Service with Kannada Support

echo "🔄 Restarting HeyGem Chatterbox Service"
echo "========================================"

# Step 1: Copy updated service file
echo "📝 Updating service file..."
sudo cp /nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox/heygem-chatterbox.service /etc/systemd/system/

# Step 2: Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Step 3: Restart service
echo "🔄 Restarting heygem-chatterbox service..."
sudo systemctl restart heygem-chatterbox.service

# Step 4: Check status
echo ""
echo "✅ Service restarted! Checking status..."
sleep 3
sudo systemctl status heygem-chatterbox.service --no-pager

echo ""
echo "📊 Service Logs (last 20 lines):"
sudo journalctl -u heygem-chatterbox.service -n 20 --no-pager

echo ""
echo "✅ Done! Service is running with Kannada support."
echo ""
echo "Test with:"
echo "  ./test_kannada.sh"
