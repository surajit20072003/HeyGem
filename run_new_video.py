#!/usr/bin/env python3
"""
Generate Talking Video: WhatsApp Video + Modi Audio
"""
import requests
import json
import time

# Configuration
VIDEO_FILE = "WhatsApp Video 2025-12-23 at 2.15.48 PM.mp4"
AUDIO_FILE = "modi.wav"
GPU_PORT = 8390
TASK_CODE = f"talking_video_{int(time.time())}"

print("=" * 70)
print("🎬 HeyGem Talking Head Video Generator")
print("=" * 70)
print(f"📹 Video: {VIDEO_FILE}")
print(f"🎤 Audio: {AUDIO_FILE}")
print(f"🔖 Task Code: {TASK_CODE}")
print("=" * 70)

# Submit task
print("\n📤 Submitting task to GPU 0...")

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
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if not result.get('success'):
        print("\n❌ Task submission failed!")
        exit(1)
    
    print("\n✅ Task submitted successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)

# Monitor progress
print("\n⏳ Monitoring progress (this may take a few minutes)...\n")

max_wait = 600  # 10 minutes
check_interval = 5
elapsed = 0

while elapsed < max_wait:
    try:
        response = requests.get(
            f"http://127.0.0.1:{GPU_PORT}/easy/query?code={TASK_CODE}",
            timeout=10
        )
        
        data = response.json().get('data', {})
        progress = data.get('progress', 0)
        status = data.get('status', 'unknown')
        
        print(f"[{elapsed:3d}s] Progress: {progress}% | Status: {status}")
        
        # Check if completed
        if progress >= 100 or status == 2:
            print("\n✅ Video generation completed!")
            print(f"\n📁 Output location:")
            print(f"   Host: ~/heygem_data/gpu0/temp/{TASK_CODE}-r.mp4")
            print(f"\n💡 Copy to current directory:")
            print(f"   cp ~/heygem_data/gpu0/temp/{TASK_CODE}-r.mp4 ./output_video.mp4")
            print("\n" + "=" * 70)
            break
        
        time.sleep(check_interval)
        elapsed += check_interval
        
    except Exception as e:
        print(f"   Error: {e}")
        time.sleep(check_interval)
        elapsed += check_interval

if elapsed >= max_wait:
    print(f"\n⏰ Timeout after {max_wait} seconds")
    print("   Check logs: docker logs heygem-gpu0")

print("\n" + "=" * 70)
