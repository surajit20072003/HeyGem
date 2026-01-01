#!/usr/bin/env python3
"""
Test if HeyGem API supports multiple input videos
"""
import requests
import json

print("=" * 80)
print("🧪 Testing HeyGem API - Multiple Video Input Support")
print("=" * 80)

API_URL = "http://localhost:8390/easy/submit"

# Test 1: Single video (current method)
print("\n1️⃣ Test 1: Single video (baseline)")
payload_single = {
    "audio_url": "/code/data/face2face/modi.wav",
    "video_url": "/code/data/face2face/input_video02.mp4",
    "code": "test_single_video",
    "chaofen": 1,
    "watermark_switch": 0,
    "pn": 1
}

print(f"Payload: {json.dumps(payload_single, indent=2)}")

try:
    response = requests.post(API_URL, json=payload_single, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.json().get('success'):
        print("✅ Single video: WORKS")
        # Cancel this task
        requests.get(f"http://localhost:8390/easy/query?code=test_single_video")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Multiple videos as array
print("\n2️⃣ Test 2: Multiple videos (video_urls array)")
payload_multi_array = {
    "audio_url": "/code/data/face2face/modi.wav",
    "video_urls": [  # Trying array instead of single URL
        "/code/data/face2face/input_video02.mp4",
        "/code/data/face2face/input_video.mp4"
    ],
    "code": "test_multi_array",
    "chaofen": 1,
    "watermark_switch": 0,
    "pn": 1
}

print(f"Payload: {json.dumps(payload_multi_array, indent=2)}")

try:
    response = requests.post(API_URL, json=payload_multi_array, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.json().get('success'):
        print("✅ Multiple videos (array): WORKS!")
    else:
        print("❌ Multiple videos (array): NOT SUPPORTED or ERROR")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Multiple videos as comma-separated string
print("\n3️⃣ Test 3: Multiple videos (comma-separated string)")
payload_multi_string = {
    "audio_url": "/code/data/face2face/modi.wav",
    "video_url": "/code/data/face2face/input_video02.mp4,/code/data/face2face/input_video.mp4",
    "code": "test_multi_string",
    "chaofen": 1,
    "watermark_switch": 0,
    "pn": 1
}

print(f"Payload: {json.dumps(payload_multi_string, indent=2)}")

try:
    response = requests.post(API_URL, json=payload_multi_string, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.json().get('success'):
        print("✅ Multiple videos (string): WORKS!")
    else:
        print("❌ Multiple videos (string): NOT SUPPORTED or ERROR")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Check for video_list parameter
print("\n4️⃣ Test 4: video_list parameter")
payload_video_list = {
    "audio_url": "/code/data/face2face/modi.wav",
    "video_list": [
        "/code/data/face2face/input_video02.mp4",
        "/code/data/face2face/input_video.mp4"
    ],
    "code": "test_video_list",
    "chaofen": 1,
    "watermark_switch": 0,
    "pn": 1
}

print(f"Payload: {json.dumps(payload_video_list, indent=2)}")

try:
    response = requests.post(API_URL, json=payload_video_list, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.json().get('success'):
        print("✅ video_list parameter: WORKS!")
    else:
        print("❌ video_list parameter: NOT SUPPORTED or ERROR")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("📝 Test Summary:")
print("=" * 80)
print("If none of the multi-video tests worked, HeyGem API does NOT support")
print("multiple input videos directly. You'll need to pre-combine videos.")
print("=" * 80)
