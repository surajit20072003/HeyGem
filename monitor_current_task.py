#!/usr/bin/env python3
"""
Monitor ongoing HeyGem task by checking output file creation
"""
import time
import os
import subprocess
from datetime import datetime

TASK_CODE = "perf_test_1766646574"
OUTPUT_PATH = f"/root/heygem_data/gpu0/temp/{TASK_CODE}-r.mp4"
CHECK_INTERVAL = 10  # seconds
MAX_WAIT = 1800  # 30 minutes

print("=" * 80)
print("🔍 HeyGem Task Monitor - File-based Progress")
print("=" * 80)
print(f"Task Code: {TASK_CODE}")
print(f"Watching: {OUTPUT_PATH}")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

def get_gpu_stats():
    """Get GPU utilization and memory"""
    try:
        result = subprocess.run([
            'nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, check=True)
        
        for line in result.stdout.strip().split('\n'):
            parts = [x.strip() for x in line.split(',')]
            if parts[0] == '0':
                return f"GPU 0: {parts[1]}% util, {int(parts[2])/1024:.1f} GB"
    except:
        pass
    return "GPU stats unavailable"

def check_temp_dir():
    """Check temp directory for processing artifacts"""
    temp_dir = f"/root/heygem_data/gpu0/temp"
    try:
        result = subprocess.run(
            ['ls', '-lh', temp_dir],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split('\n')
        
        # Count files
        avi_count = result.stdout.count('.avi')
        png_count = result.stdout.count('.png')
        
        return f"AVIs: {avi_count}, PNGs: {png_count}"
    except:
        return "N/A"

start_time = time.time()
elapsed = 0

print("\n⏳ Monitoring (press Ctrl+C to stop)...\n")

try:
    while elapsed < MAX_WAIT:
        # Check if output file exists
        if os.path.exists(OUTPUT_PATH):
            file_size = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)  # MB
            
            print("\n" + "=" * 80)
            print("✅ OUTPUT FILE CREATED!")
            print("=" * 80)
            print(f"📁 Location: {OUTPUT_PATH}")
            print(f"📊 Size: {file_size:.1f} MB")
            print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
            print("=" * 80)
            
            # Copy to main directory
            output_name = f"output_{TASK_CODE}.mp4"
            subprocess.run([
                'cp', OUTPUT_PATH,
                f"/nvme0n1-disk/HeyGem/{output_name}"
            ])
            print(f"✅ Copied to: /nvme0n1-disk/HeyGem/{output_name}")
            print("=" * 80)
            break
        
        # Print status
        gpu_stats = get_gpu_stats()
        temp_info = check_temp_dir()
        
        print(f"[{elapsed:4d}s] {gpu_stats} | {temp_info} | Waiting for output...")
        
        time.sleep(CHECK_INTERVAL)
        elapsed += CHECK_INTERVAL

    if elapsed >= MAX_WAIT:
        print(f"\n⏰ Max wait time ({MAX_WAIT/60:.0f} min) reached")
        print("   Task may still be processing in background")

except KeyboardInterrupt:
    print("\n\n⚠️  Monitoring stopped by user")
    print(f"   Elapsed: {elapsed/60:.1f} minutes")
    print("   Task continues in background")

print("\n🎉 Monitor completed!")
print("=" * 80)
