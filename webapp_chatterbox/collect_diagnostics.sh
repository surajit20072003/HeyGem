#!/bin/bash
echo "============================================="
echo "📊 Server Diagnostic Tool"
echo "============================================="

echo -e "\n1. System Info:"
hostname
cat /etc/os-release | grep PRETTY_NAME
uname -r

echo -e "\n2. NVIDIA Driver & CUDA:"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

echo -e "\n3. Docker Image Hash (Critical):"
sudo docker images guiji2025/heygem.ai --digests

echo -e "\n4. Container Process Info:"
sudo docker exec heygem-gpu0 ps aux | head -n 10

echo -e "\n5. Model Files Check (Top 20):"
sudo docker exec heygem-gpu0 find /code -name "*.pth" -o -name "*.pt" -o -name "*.onnx" -o -name "*.bin" | head -n 20

echo -e "\n6. Checkpoints Directory:"
sudo docker exec heygem-gpu0 ls -la /code/checkpoints 2>/dev/null || echo "No /code/checkpoints found"
sudo docker exec heygem-gpu0 ls -la /code/weights 2>/dev/null || echo "No /code/weights found"

echo -e "\n7. PyTorch Version:"
sudo docker exec heygem-gpu0 python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.version.cuda}, CuDNN: {torch.backends.cudnn.version()}')"

echo -e "\n8. Container Environment Variables:"
sudo docker exec heygem-gpu0 env | grep -E "CUDA|nvidia|LANG|LC_"

echo -e "\n9. Temp Directory Permissions:"
sudo docker exec heygem-gpu0 ls -ld /code/data /code/data/temp
