#!/usr/bin/env python3
"""
HeyGem.ai API Test Script
Simple script to test video generation API
"""

import requests
import json
import time
import sys

# API Configuration
BASE_URL = "http://127.0.0.1:8383"
SUBMIT_ENDPOINT = f"{BASE_URL}/easy/submit"
QUERY_ENDPOINT = f"{BASE_URL}/easy/query"

def test_api_connection():
    """Test if API is accessible"""
    print("🔍 Testing API connection...")
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✅ API is running (Status: {response.status_code})")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

def submit_video_task(audio_path, video_path, task_code="test_001"):
    """
    Submit video generation task
    
    Args:
        audio_path: Path to audio file (inside Docker container)
        video_path: Path to source video file (inside Docker container)
        task_code: Unique task identifier
    """
    print(f"\n📤 Submitting video generation task...")
    print(f"   Audio: {audio_path}")
    print(f"   Video: {video_path}")
    print(f"   Code: {task_code}")
    
    payload = {
        "audio_url": audio_path,
        "video_url": video_path,
        "code": task_code,
        "chaofen": 0,
        "watermark_switch": 0,
        "pn": 1
    }
    
    try:
        response = requests.post(
            SUBMIT_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"   Response Status: {response.status_code}")
        result = response.json()
        print(f"   Response: {json.dumps(result, indent=2)}")
        return result, task_code
    except requests.exceptions.RequestException as e:
        print(f"❌ Error submitting task: {e}")
        return None, None

def check_task_progress(task_code):
    """
    Check progress of submitted task
    
    Args:
        task_code: Task identifier from submit
    """
    print(f"\n🔄 Checking progress for task: {task_code}")
    
    try:
        response = requests.get(
            f"{QUERY_ENDPOINT}?code={task_code}",
            timeout=10
        )
        
        result = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(result, indent=2)}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking progress: {e}")
        return None

def monitor_task(task_code, max_wait=300, check_interval=5):
    """
    Monitor task until completion
    
    Args:
        task_code: Task identifier
        max_wait: Maximum wait time in seconds (default: 5 minutes)
        check_interval: Seconds between checks (default: 5)
    """
    print(f"\n⏳ Monitoring task {task_code}...")
    print(f"   Max wait: {max_wait}s, Check interval: {check_interval}s")
    
    elapsed = 0
    while elapsed < max_wait:
        result = check_task_progress(task_code)
        
        if result:
            # Check if task is complete (adjust based on actual API response)
            status = result.get('status', '')
            progress = result.get('progress', 0)
            
            print(f"   [{elapsed}s] Status: {status}, Progress: {progress}%")
            
            if status == 'completed' or progress == 100:
                print(f"✅ Task completed!")
                return result
        
        time.sleep(check_interval)
        elapsed += check_interval
    
    print(f"⏰ Timeout after {max_wait}s")
    return None

def main():
    """Main test function"""
    print("=" * 60)
    print("HeyGem.ai API Test Script")
    print("=" * 60)
    
    # Test connection
    if not test_api_connection():
        print("\n❌ API is not running. Start Docker container first:")
        print("   docker start heygem-gen-video")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("API Usage Examples")
    print("=" * 60)
    
    print("""
📝 To generate a video, you need:
   1. Audio file (.wav) - inside Docker container
   2. Source video file (.mp4) - your face video
   
   Files should be in: ~/heygem_data/face2face/
   
Example usage:
    
    # Submit task
    result, code = submit_video_task(
        audio_path="/code/data/your_audio.wav",
        video_path="/code/data/your_video.mp4",
        task_code="my_task_001"
    )
    
    # Check progress
    progress = check_task_progress(code)
    
    # Monitor until complete
    final = monitor_task(code)
""")
    
    print("\n" + "=" * 60)
    print("Ready to use! Modify this script with your file paths.")
    print("=" * 60)

if __name__ == "__main__":
    main()
