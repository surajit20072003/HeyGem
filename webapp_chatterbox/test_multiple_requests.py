#!/usr/bin/env python3
"""
Simple test script for Dual TTS API
Tests multiple small text requests
"""

import requests
import time
import json

API_BASE = "http://localhost:5003"

# Test texts - small and varied
TEST_TEXTS = [
    "Hello, this is a simple test.",
    "The weather is nice today.",
    "Welcome to AI video generation!",
    "Testing voice cloning feature.",
    "This system uses dual GPUs for faster processing."
]

def submit_task(text):
    """Submit a text generation task"""
    print(f"\n📤 Submitting: '{text[:40]}...'")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/generate",
            data={"text": text},
            timeout=30
        )
        
        if response.status_code == 202:
            result = response.json()
            task_id = result.get("task_id")
            print(f"   ✅ Task submitted: {task_id}")
            return task_id
        else:
            print(f"   ❌ Failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def check_status(task_id):
    """Check task status"""
    try:
        response = requests.get(f"{API_BASE}/api/status/{task_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"   ❌ Status check error: {e}")
        return None

def wait_for_completion(task_id, max_wait=120):
    """Wait for task to complete"""
    print(f"\n⏳ Waiting for task {task_id}...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        status = check_status(task_id)
        
        if status:
            state = status.get("status")
            progress = status.get("progress", 0)
            
            if state == "completed":
                timing = status.get("timing", {})
                print(f"   ✅ Completed!")
                print(f"   ⏱️  TTS: {timing.get('tts_time', 'N/A'):.2f}s" if timing.get('tts_time') else "   ⏱️  TTS: N/A")
                print(f"   ⏱️  Video: {timing.get('video_time', 'N/A'):.2f}s" if timing.get('video_time') else "   ⏱️  Video: N/A")
                print(f"   ⏱️  Total: {timing.get('total_time', 'N/A'):.2f}s" if timing.get('total_time') else "   ⏱️  Total: N/A")
                return True
                
            elif state == "failed":
                error = status.get("error", "Unknown error")
                print(f"   ❌ Failed: {error}")
                return False
                
            else:
                print(f"   📊 Status: {state} ({progress}%)")
        
        time.sleep(3)
    
    print(f"   ⏰ Timeout after {max_wait}s")
    return False

def check_queue():
    """Check current queue status"""
    try:
        response = requests.get(f"{API_BASE}/api/queue")
        if response.status_code == 200:
            data = response.json()
            print("\n📋 Queue Status:")
            print(f"   Queue size: {data.get('queue_size', 0)}")
            
            for gpu_id, status in data.get('gpus', {}).items():
                busy = "🔴 Busy" if status['busy'] else "🟢 Free"
                util = status.get('gpu_utilization', 0)
                print(f"   GPU {gpu_id}: {busy} | Usage: {util}%")
    except Exception as e:
        print(f"   ❌ Queue check error: {e}")

def main():
    print("=" * 60)
    print("🚀 Dual TTS API Test Script")
    print("=" * 60)
    
    # Check health
    try:
        response = requests.get(f"{API_BASE}/api/health")
        if response.status_code == 200:
            print("✅ API is healthy")
        else:
            print("❌ API health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return
    
    # Submit all tasks
    task_ids = []
    for text in TEST_TEXTS:
        task_id = submit_task(text)
        if task_id:
            task_ids.append(task_id)
        time.sleep(1)  # Small delay between submissions
    
    print(f"\n📊 Submitted {len(task_ids)} tasks")
    
    # Check queue
    check_queue()
    
    # Wait for all tasks
    print("\n" + "=" * 60)
    print("⏳ Waiting for tasks to complete...")
    print("=" * 60)
    
    results = []
    for task_id in task_ids:
        success = wait_for_completion(task_id)
        results.append(success)
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 Test Summary")
    print("=" * 60)
    successful = sum(results)
    print(f"   Total tasks: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {len(results) - successful}")
    print(f"   Success rate: {(successful/len(results)*100):.1f}%")
    
    # Final queue check
    check_queue()
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    main()
