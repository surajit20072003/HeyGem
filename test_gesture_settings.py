#!/usr/bin/env python3
"""
Test Different HeyGem Gesture Settings
Tests chaofen parameter (0, 1, 2) to see gesture variation
"""
import requests
import json
import time
import subprocess
import os
import sys
from datetime import datetime

# Configuration
VIDEO_FILE = "input_video02.mp4"
AUDIO_FILE = "modi.wav"
GPU_ID = 0
GPU_PORT = 8390

# Get chaofen value from command line or use default
CHAOFEN = int(sys.argv[1]) if len(sys.argv) > 1 else 0

TASK_CODE = f"gesture_test_chaofen{CHAOFEN}_{int(time.time())}"
OUTPUT_NAME = f"output_chaofen_{CHAOFEN}.mp4"

print("=" * 80)
print("🎭 HeyGem Gesture Settings Test")
print("=" * 80)
print(f"📹 Video: {VIDEO_FILE}")
print(f"🎤 Audio: {AUDIO_FILE}")
print(f"🎯 GPU: {GPU_ID} (Port: {GPU_PORT})")
print(f"🎲 CHAOFEN Parameter: {CHAOFEN}")
print(f"🔖 Task Code: {TASK_CODE}")
print(f"📁 Output: {OUTPUT_NAME}")
print("=" * 80)

# Copy files to GPU data directory
print("\n📁 Copying files to GPU data directory...")
gpu_data_dir = os.path.expanduser("~/heygem_data/gpu0/face2face/")
os.makedirs(gpu_data_dir, exist_ok=True)

try:
    subprocess.run(['cp', f'/nvme0n1-disk/HeyGem/{VIDEO_FILE}', gpu_data_dir], check=True)
    subprocess.run(['cp', f'/nvme0n1-disk/HeyGem/{AUDIO_FILE}', gpu_data_dir], check=True)
    print("   ✅ Files copied successfully")
except Exception as e:
    print(f"   ❌ Error copying files: {e}")
    exit(1)

# Submit task with specific chaofen setting
print(f"\n📤 Submitting task with chaofen={CHAOFEN}...")
start_time = time.time()

payload = {
    "audio_url": f"/code/data/face2face/{AUDIO_FILE}",
    "video_url": f"/code/data/face2face/{VIDEO_FILE}",
    "code": TASK_CODE,
    "chaofen": CHAOFEN,  # Testing this parameter
    "watermark_switch": 0,
    "pn": 1
}

print(f"   Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(
        f"http://127.0.0.1:{GPU_PORT}/easy/submit",
        json=payload,
        timeout=30
    )
    
    result = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(result, indent=2)}")
    
    if not result.get('success'):
        print(f"   ❌ Task submission failed!")
        exit(1)
    
    print("   ✅ Task submitted successfully!")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Monitor progress
print("\n⏳ Monitoring progress...")
print("   💡 Will check every 30 seconds (use Ctrl+C to stop)\n")

output_file = os.path.expanduser(f"~/heygem_data/gpu0/temp/{TASK_CODE}-r.mp4")
elapsed = 0
check_interval = 30

while True:
    try:
        # Check if output file exists
        if os.path.exists(output_file):
            # Wait for file write completion
            print("\n⏳ Video file detected! Waiting for complete write...")
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
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            
            print("\n" + "=" * 80)
            print("✅ VIDEO GENERATION COMPLETE!")
            print("=" * 80)
            print(f"⏱️  Total Time: {total_time/60:.2f} minutes")
            print(f"📁 Source: {output_file}")
            print(f"📊 Size: {file_size:.1f} MB")
            print("=" * 80)
            
            # Copy to main directory with specific name
            print(f"\n📋 Copying to /nvme0n1-disk/HeyGem/{OUTPUT_NAME}...")
            subprocess.run([
                'cp',
                output_file,
                f"/nvme0n1-disk/HeyGem/{OUTPUT_NAME}"
            ])
            
            # Verify copy
            copied_size = os.path.getsize(f"/nvme0n1-disk/HeyGem/{OUTPUT_NAME}") / (1024 * 1024)
            if abs(copied_size - file_size) < 0.1:
                print(f"✅ Copy verified: {OUTPUT_NAME} ({copied_size:.1f} MB)")
            else:
                print(f"⚠️  Copy size mismatch! Original: {file_size:.1f} MB, Copied: {copied_size:.1f} MB")
            
            print("\n" + "=" * 80)
            print(f"🎉 Test completed for CHAOFEN={CHAOFEN}")
            print(f"📹 Output: /nvme0n1-disk/HeyGem/{OUTPUT_NAME}")
            print("=" * 80)
            break
        
        # Check API progress
        try:
            response = requests.get(
                f"http://127.0.0.1:{GPU_PORT}/easy/query?code={TASK_CODE}",
                timeout=10
            )
            
            data = response.json().get('data', {})
            progress = data.get('progress', 0)
            msg = data.get('msg', '')
            
            print(f"[{elapsed:4d}s / {elapsed//60:2d}m] Progress: {progress:3d}% | {msg}")
            
        except Exception as e:
            print(f"[{elapsed:4d}s] Monitoring... (API check failed)")
        
        time.sleep(check_interval)
        elapsed += check_interval
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Monitoring stopped by user")
        print(f"   Task continues in background!")
        print(f"   Check: {output_file}")
        break

print("\n🏁 Done!")
