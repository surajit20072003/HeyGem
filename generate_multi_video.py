#!/usr/bin/env python3
"""
Multi-Video Input Generator
Uses HeyGem's native support for multiple input videos
"""
import requests
import json
import time
import subprocess
import os
from datetime import datetime

print("=" * 80)
print("🎬 HeyGem Multi-Video Input - No More Gesture Loops!")
print("=" * 80)

# Configuration
INPUT_VIDEOS = [
    "input_video02.mp4",
    "input_video03.mp4",
    "input_video04.mp4",
    # Add more videos here!
]
AUDIO_FILE = "modi.wav"
GPU_ID = 0
GPU_PORT = 8390
TASK_CODE = f"multi_video_{int(time.time())}"

print(f"\n📹 Input Videos ({len(INPUT_VIDEOS)} clips):")
for i, vid in enumerate(INPUT_VIDEOS, 1):
    if os.path.exists(f"/nvme0n1-disk/HeyGem/{vid}"):
        size = os.path.getsize(f"/nvme0n1-disk/HeyGem/{vid}") / (1024*1024)
        print(f"   {i}. {vid} ({size:.1f} MB) ✅")
    else:
        print(f"   {i}. {vid} ❌ NOT FOUND")

print(f"🎤 Audio: {AUDIO_FILE}")
print(f"🎯 GPU: {GPU_ID} (Port: {GPU_PORT})")
print(f"🔖 Task Code: {TASK_CODE}")

# Copy files to GPU data directory
print("\n📁 Copying files to GPU data directory...")
gpu_data_dir = os.path.expanduser("~/heygem_data/gpu0/face2face/")
os.makedirs(gpu_data_dir, exist_ok=True)

try:
    # Copy all videos
    for vid in INPUT_VIDEOS:
        src = f'/nvme0n1-disk/HeyGem/{vid}'
        if os.path.exists(src):
            subprocess.run(['cp', src, gpu_data_dir], check=True)
    
    # Copy audio
    subprocess.run(['cp', f'/nvme0n1-disk/HeyGem/{AUDIO_FILE}', gpu_data_dir], check=True)
    print("   ✅ All files copied successfully")
except Exception as e:
    print(f"   ❌ Error copying files: {e}")
    exit(1)

# Submit task with multiple videos
print(f"\n📤 Submitting task with {len(INPUT_VIDEOS)} input videos...")
print("   HeyGem will randomly select gestures from all videos! 🎲")

# Create video URLs list
video_urls = [f"/code/data/face2face/{vid}" for vid in INPUT_VIDEOS]

payload = {
    "audio_url": f"/code/data/face2face/{AUDIO_FILE}",
    "video_url": video_urls[0],  # Primary video (required)
    "video_urls": video_urls,     # All videos for variety
    "code": TASK_CODE,
    "chaofen": 1,
    "watermark_switch": 0,
    "pn": 1
}

print(f"\n   Payload:")
print(json.dumps(payload, indent=2))

try:
    response = requests.post(
        f"http://127.0.0.1:{GPU_PORT}/easy/submit",
        json=payload,
        timeout=30
    )
    
    result = response.json()
    print(f"\n   Status: {response.status_code}")
    print(f"   Response: {json.dumps(result, indent=2)}")
    
    if not result.get('success'):
        print(f"   ❌ Task submission failed!")
        exit(1)
    
    print("   ✅ Task submitted successfully!")
    print(f"   🎭 Using {len(INPUT_VIDEOS)} videos for gesture variety!")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Monitor progress
print("\n⏳ Monitoring progress...")
print("   💡 Check every 30 seconds (Ctrl+C to stop)\n")

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
            
            size1 = os.path.getsize(output_file)
            time.sleep(2)
            size2 = os.path.getsize(output_file)
            
            if size1 != size2:
                print("⚠️  File still being written, waiting 10 more seconds...")
                time.sleep(10)
            
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            
            print("\n" + "=" * 80)
            print("✅ MULTI-VIDEO GENERATION COMPLETE!")
            print("=" * 80)
            print(f"⏱️  Total Time: {elapsed/60:.2f} minutes")
            print(f"📁 Source: {output_file}")
            print(f"📊 Size: {file_size:.1f} MB")
            print(f"🎭 Gesture Variety: {len(INPUT_VIDEOS)} different input videos")
            print("=" * 80)
            
            # Copy to main directory
            output_name = f"output_multi_{TASK_CODE}.mp4"
            print(f"\n📋 Copying to /nvme0n1-disk/HeyGem/{output_name}...")
            
            import shutil
            shutil.copy(output_file, f"/nvme0n1-disk/HeyGem/{output_name}")
            
            copied_size = os.path.getsize(f"/nvme0n1-disk/HeyGem/{output_name}") / (1024 * 1024)
            if abs(copied_size - file_size) < 0.1:
                print(f"✅ Copy verified: {output_name} ({copied_size:.1f} MB)")
            
            print("\n" + "=" * 80)
            print(f"🎉 Video with VARIED GESTURES ready!")
            print(f"📹 Download: scp root@69.30.204.142:/nvme0n1-disk/HeyGem/{output_name} ./")
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
            print(f"[{elapsed:4d}s] Monitoring...")
        
        time.sleep(check_interval)
        elapsed += check_interval
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Monitoring stopped")
        print(f"   Task continues in background!")
        break

print("\n🏁 Done!")
