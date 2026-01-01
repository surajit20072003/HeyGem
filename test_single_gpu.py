#!/usr/bin/env python3
"""
Simple Test: Generate video using existing audio and video files
"""
import requests
import json
import time
import sys

# Configuration - Change these paths to your files
VIDEO_FILE = "WhatsApp Video 2025-12-18 at 3.25.47 PM.mp4"
AUDIO_FILE = "modi.wav"
GPU_PORT = 8390  # GPU 0

# API endpoint
BASE_URL = f"http://127.0.0.1:{GPU_PORT}"
TASK_CODE = f"test_{int(time.time())}"

print("=" * 70)
print("🎬 HeyGem Single GPU Test")
print("=" * 70)
print(f"Video: {VIDEO_FILE}")
print(f"Audio: {AUDIO_FILE}")
print(f"GPU Port: {GPU_PORT}")
print(f"Task Code: {TASK_CODE}")
print("=" * 70)

# Submit task
print("\n📤 Submitting task...")

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
        f"{BASE_URL}/easy/submit",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code != 200 or not result.get('success'):
        print("\n❌ Task submission failed!")
        sys.exit(1)
    
    print("\n✅ Task submitted successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)

# Monitor progress
print("\n⏳ Monitoring progress (this may take a few minutes)...\n")

max_wait = 600  # 10 minutes
check_interval = 5
elapsed = 0

while elapsed < max_wait:
    try:
        response = requests.get(
            f"{BASE_URL}/easy/query?code={TASK_CODE}",
            timeout=10
        )
        
        data = response.json()
        task_data = data.get('data', {})
        progress = task_data.get('progress', 0)
        status = task_data.get('status', 'unknown')
        
        print(f"[{elapsed:3d}s] Progress: {progress}% | Status: {status}")
        
        # Check if completed
        if progress >= 100 or status == 'completed':
            print("\n✅ Video generation completed!")
            print(f"\nFull result:")
            print(json.dumps(data, indent=2))
            print("\n📁 Check output in Docker container's /code/data/face2face/temp/")
            print(f"   File name: {TASK_CODE}-r.mp4")
            break
        
        time.sleep(check_interval)
        elapsed += check_interval
        
    except Exception as e:
        print(f"   Error: {e}")
        time.sleep(check_interval)
        elapsed += check_interval

if elapsed >= max_wait:
    print(f"\n⏰ Timeout after {max_wait} seconds")

print("\n" + "=" * 70)
