#!/usr/bin/env python3
"""
Generate Talking Video using HeyGem API
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://127.0.0.1:8390"
#BASE_URL = "http://69.30.204.142:8390"
TASK_CODE = "whatsapp_video_004"

# File paths (as Docker sees them)
#AUDIO_PATH = "./data/audio.mp3"
#VIDEO_PATH = "./data/avatar_silent.mp4"
AUDIO_PATH = "/root/heygem_data/face2face/audio.wav"
VIDEO_PATH = "/root/heygem_data/face2face/avatar.mp4"


print("=" * 60)
print("🎬 HeyGem Video Generation")
print("=" * 60)

# Step 1: Submit task
print("\n📤 Step 1: Submitting video generation task...")
print(f"   Audio: {AUDIO_PATH}")
print(f"   Video: {VIDEO_PATH}")
print(f"   Task Code: {TASK_CODE}")

payload = {
    "audio_url": AUDIO_PATH,
    "video_url": VIDEO_PATH,
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
    
    print(f"   Response Status: {response.status_code}")
    result = response.json()
    print(f"   Response: {json.dumps(result, indent=2)}")
    
    if response.status_code != 200:
        print(f"\n❌ Error submitting task!")
        exit(1)
    
    print("\n✅ Task submitted successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)

# Step 2: Monitor progress
print("\n⏳ Step 2: Monitoring task progress...")
print("   (This may take a few minutes...)\n")

max_wait = 600  # 10 minutes
check_interval = 10  # Check every 10 seconds
elapsed = 0

while elapsed < max_wait:
    try:
        progress_response = requests.get(
            f"{BASE_URL}/easy/query?code={TASK_CODE}",
            timeout=10
        )
        
        progress_result = progress_response.json()
        
        # Print progress
        #status = progress_result.get('status', 'unknown')
        #progress = progress_result.get('progress', 0)
        data = progress_result.get('data', {})
        status = data.get('status', 'unknown')
        progress = data.get('progress', 0)

        
        print(f"   [{elapsed}s] Status: {status}")
        
        # Check if completed (adjust based on actual API response)
        if 'result' in progress_result or status == 'completed':
            print("\n✅ Video generation completed!")
            print(f"\nFinal Result:")
            print(json.dumps(progress_result, indent=2))
            print("\n📁 Check output in: /root/heygem_data/face2face/result/")
            break
        
        time.sleep(check_interval)
        elapsed += check_interval
        
    except Exception as e:
        print(f"   Error checking progress: {e}")
        time.sleep(check_interval)
        elapsed += check_interval

if elapsed >= max_wait:
    print(f"\n⏰ Timeout after {max_wait} seconds")
    print("   Check logs: docker logs heygem-gen-video")

print("\n" + "=" * 60)
