#!/usr/bin/env python3
"""
Single GPU Video Generation with Performance Tracking
Tracks: Total time, GPU memory usage, system stats
"""
import requests
import json
import time
import subprocess
import os
from datetime import datetime

# Configuration
VIDEO_FILE = "input_video02.mp4"
AUDIO_FILE = "input_audio.mp3"
GPU_ID = 2 
GPU_PORT = 8392
TASK_CODE = f"perf_test_{int(time.time())}"
STATS_FILE = f"performance_stats_{TASK_CODE}.json"

print("=" * 80)
print("🎬 HeyGem Single GPU Performance Test")
print("=" * 80)
print(f"📹 Video: {VIDEO_FILE}")
print(f"🎤 Audio: {AUDIO_FILE}")
print(f"🔖 Task Code: {TASK_CODE}")
print(f"🎯 GPU ID: {GPU_ID}")
print(f"📊 Stats File: {STATS_FILE}")
print("=" * 80)

# Performance tracking
stats = {
    "task_code": TASK_CODE,
    "video_file": VIDEO_FILE,
    "audio_file": AUDIO_FILE,
    "gpu_id": GPU_ID,
    "start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    "gpu_snapshots": []
}

def get_gpu_stats():
    """Get current GPU memory usage"""
    try:
        result = subprocess.run([
            'nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used,memory.total',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split('\n')
        for line in lines:
            parts = [x.strip() for x in line.split(',')]
            if parts[0] == str(GPU_ID):
                return {
                    "gpu_id": int(parts[0]),
                    "utilization": f"{parts[1]}%",
                    "memory_used_mb": int(parts[2]),
                    "memory_total_mb": int(parts[3]),
                    "memory_used_gb": round(int(parts[2]) / 1024, 2),
                    "memory_total_gb": round(int(parts[3]) / 1024, 2)
                }
    except Exception as e:
        return {"error": str(e)}
    return {}

# Initial GPU stats
print("\n📊 Initial GPU Status:")
initial_gpu = get_gpu_stats()
print(f"   GPU {GPU_ID}: {initial_gpu.get('memory_used_gb', 'N/A')} GB / {initial_gpu.get('memory_total_gb', 'N/A')} GB")
print(f"   Utilization: {initial_gpu.get('utilization', 'N/A')}")
stats["initial_gpu"] = initial_gpu

# Copy files to GPU data directory
print("\n📁 Copying files to GPU data directory...")
gpu_data_dir = os.path.expanduser(f"~/heygem_data/gpu{GPU_ID}/face2face/")
os.makedirs(gpu_data_dir, exist_ok=True)

try:
    subprocess.run(['cp', f'/nvme0n1-disk/HeyGem/{VIDEO_FILE}', gpu_data_dir], check=True)
    subprocess.run(['cp', f'/nvme0n1-disk/HeyGem/{AUDIO_FILE}', gpu_data_dir], check=True)
    print("   ✅ Files copied successfully")
except Exception as e:
    print(f"   ❌ Error copying files: {e}")
    exit(1)

# Submit task
print("\n📤 Submitting task to GPU...")
start_time = time.time()
stats["submit_timestamp"] = start_time

payload = {
    "audio_url": f"/code/data/face2face/{AUDIO_FILE}",
    "video_url": f"/code/data/face2face/{VIDEO_FILE}",
    "code": TASK_CODE,
    "chaofen": 0,
    "watermark_switch": 0,
    "pn": 1
}

try:
    response = requests.post(
        f"http://127.0.0.1:{GPU_PORT}/easy/submit",
        json=payload,
        timeout=30
    )
    
    result = response.json()
    print(f"   Status: {response.status_code}")
    
    if not result.get('success'):
        print(f"   ❌ Task submission failed: {result}")
        exit(1)
    
    print("   ✅ Task submitted successfully!")
    stats["submission_response"] = result
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Monitor progress with GPU stats
print("\n⏳ Monitoring progress with GPU tracking...")
print("   ⚠️  NO TIMEOUT - Will wait as long as needed!")
print("   💡 Press Ctrl+C to stop monitoring (task will continue in background)\n")

check_interval = 10
elapsed = 0
last_progress = -1
output_file = os.path.expanduser(f"~/heygem_data/gpu{GPU_ID}/temp/{TASK_CODE}-r.mp4")

# Infinite loop - will only exit when file is created or user interrupts
while True:
    try:
        # Check if output file exists (most reliable detection)
        if os.path.exists(output_file):
            # Wait for file write to complete
            print("\n⏳ Video file detected! Waiting to ensure complete write...")
            time.sleep(5)
            
            # Verify file size stability
            size1 = os.path.getsize(output_file)
            time.sleep(2)
            size2 = os.path.getsize(output_file)
            
            if size1 != size2:
                print("⚠️  File still being written, waiting 10 more seconds...")
                time.sleep(10)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print("\n✅ Video generation completed!")
            print("=" * 80)
            
            # Final GPU stats
            final_gpu = get_gpu_stats()
            stats["final_gpu"] = final_gpu
            stats["end_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            stats["total_time_seconds"] = round(total_time, 2)
            stats["total_time_minutes"] = round(total_time / 60, 2)
            
            # Get final task data
            try:
                response = requests.get(
                    f"http://127.0.0.1:{GPU_PORT}/easy/query?code={TASK_CODE}",
                    timeout=10
                )
                stats["final_result"] = response.json().get('data', {})
            except:
                pass
            
            # Get file size
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            
            # Print summary
            print(f"⏱️  Total Time: {stats['total_time_minutes']:.2f} minutes ({stats['total_time_seconds']:.1f} seconds)")
            print(f"🎯 GPU Used: GPU {GPU_ID}")
            print(f"💾 Peak GPU Memory: {max([s.get('gpu', {}).get('memory_used_gb', 0) for s in stats['gpu_snapshots']] or [0]):.2f} GB")
            print(f"📁 Output: {output_file} ({file_size:.1f} MB)")
            print("=" * 80)
            
            # Save stats to file
            with open(STATS_FILE, 'w') as f:
                json.dump(stats, f, indent=2)
            print(f"\n📊 Performance stats saved to: {STATS_FILE}")
            
            # Copy output with verification
            output_name = f"output_{TASK_CODE}.mp4"
            print(f"📋 Copying complete file to /nvme0n1-disk/HeyGem/{output_name}...")
            subprocess.run([
                'cp',
                output_file,
                f"/nvme0n1-disk/HeyGem/{output_name}"
            ])
            
            # Verify copy
            copied_size = os.path.getsize(f"/nvme0n1-disk/HeyGem/{output_name}") / (1024 * 1024)
            if abs(copied_size - file_size) < 0.1:
                print(f"✅ Copy verified: {output_name} ({copied_size:.1f} MB)")
            else:
                print(f"⚠️  Copy size mismatch! Original: {file_size:.1f} MB, Copied: {copied_size:.1f} MB")
            
            print("\n" + "=" * 80)
            break
        
        # Get API progress (informational only, not used for completion detection)
        try:
            response = requests.get(
                f"http://127.0.0.1:{GPU_PORT}/easy/query?code={TASK_CODE}",
                timeout=10
            )
            
            data = response.json().get('data', {})
            progress = data.get('progress', 0)
            status = data.get('status', 'unknown')
            
            # Get GPU stats
            gpu_stats = get_gpu_stats()
            
            # Log every check (progress API may not update reliably)
            snapshot = {
                "elapsed_seconds": elapsed,
                "progress": progress,
                "status": status,
                "gpu": gpu_stats,
                "timestamp": datetime.now().strftime('%H:%M:%S')
            }
            stats["gpu_snapshots"].append(snapshot)
            
            # Show status every check
            print(f"[{elapsed:4d}s / {elapsed//60:2d}m] Progress: {progress:3d}% | GPU: {gpu_stats.get('memory_used_gb', 'N/A')} GB ({gpu_stats.get('utilization', 'N/A')}) | Waiting...")
            
        except Exception as e:
            print(f"[{elapsed:4d}s] Monitoring... (API check failed, continuing)")
        
        
        time.sleep(check_interval)
        elapsed += check_interval
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring stopped by user (Ctrl+C)")
        print(f"   Elapsed: {elapsed//60} minutes {elapsed%60} seconds")
        print(f"   Task continues in background!")
        print(f"   Check output: {output_file}")
        
        # Save stats even on interrupt
        stats["status"] = "interrupted"
        stats["elapsed_at_interrupt"] = elapsed
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"   Stats saved to: {STATS_FILE}")
        break
    
    except Exception as e:
        print(f"   ⚠️  Error: {e}, continuing...")
print("\n🎉 Process completed!")
print("=" * 80)
