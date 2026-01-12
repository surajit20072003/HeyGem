#!/usr/bin/env python3
"""
Test script for atomic GPU reservation system
Tests concurrent requests to verify proper GPU locking
"""
import requests
import time
import threading
import json
from datetime import datetime

API_URL = "http://localhost:5003"

def submit_request(request_id, text, delay=0):
    """Submit a video generation request"""
    if delay > 0:
        time.sleep(delay)
    
    start_time = time.time()
    print(f"\n[Request {request_id}] Submitting at {datetime.now().strftime('%H:%M:%S')}")
    print(f"   Text: {text}")
    
    try:
        response = requests.post(
            f"{API_URL}/api/generate",
            data={"text": text},
            timeout=10
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 202:
            result = response.json()
            task_id = result.get("task_id")
            print(f"[Request {request_id}] ✅ Submitted successfully in {elapsed:.2f}s")
            print(f"   Task ID: {task_id}")
            return task_id
        else:
            print(f"[Request {request_id}] ❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"[Request {request_id}] ❌ Error: {e}")
        return None

def check_status(task_id, request_id):
    """Check task status"""
    try:
        response = requests.get(f"{API_URL}/api/status/{task_id}")
        if response.status_code == 200:
            status = response.json()
            return status
        return None
    except Exception as e:
        print(f"[Request {request_id}] Error checking status: {e}")
        return None

def check_queue():
    """Check current queue status"""
    try:
        response = requests.get(f"{API_URL}/api/queue")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error checking queue: {e}")
        return None

def test_single_request():
    """Test 1: Single request - should work normally"""
    print("\n" + "="*80)
    print(" TEST 1: Single Request")
    print("="*80)
    
    task_id = submit_request(1, "This is test number one")
    
    if task_id:
        # Wait a bit and check status
        time.sleep(2)
        status = check_status(task_id, 1)
        if status:
            print(f"\n[Request 1] Status after 2s: {status.get('status')}")
            print(f"   GPU ID: {status.get('gpu_id')}")
            print(f"   Progress: {status.get('progress')}%")

def test_concurrent_2_requests():
    """Test 2: 2 concurrent requests - should use both GPUs"""
    print("\n" + "="*80)
    print(" TEST 2: 2 Concurrent Requests (Should Use Both GPUs)")
    print("="*80)
    
    threads = []
    task_ids = [None, None]
    
    def submit_and_store(idx, text):
        task_ids[idx] = submit_request(idx + 1, text)
    
    # Submit both at the same time
    t1 = threading.Thread(target=submit_and_store, args=(0, "Concurrent test one"))
    t2 = threading.Thread(target=submit_and_store, args=(1, "Concurrent test two"))
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    # Check queue status
    time.sleep(2)
    queue_status = check_queue()
    if queue_status:
        print("\n📊 Queue Status:")
        print(json.dumps(queue_status, indent=2))

def test_queue_overflow():
    """Test 3: 5 concurrent requests - should queue 3"""
    print("\n" + "="*80)
    print(" TEST 3: Queue Overflow (5 Requests, Expected 2 GPUs + 3 Queued)")
    print("="*80)
    
    threads = []
    task_ids = [None] * 5
    
    def submit_and_store(idx, text):
        task_ids[idx] = submit_request(idx + 1, text, delay=idx*0.1)
    
    # Submit 5 requests with small delays
    for i in range(5):
        t = threading.Thread(target=submit_and_store, args=(i, f"Queue overflow test {i+1}"))
        threads.append(t)
        t.start()
    
    # Wait for all submissions
    for t in threads:
        t.join()
    
    # Check queue status immediately
    time.sleep(1)
    queue_status = check_queue()
    if queue_status:
        print("\n📊 Queue Status After Submissions:")
        print(f"   Queue Size: {queue_status.get('queue_size')}")
        print(f"   GPU 0 Busy: {queue_status.get('gpus', {}).get('0', {}).get('busy')}")
        print(f"   GPU 1 Busy: {queue_status.get('gpus', {}).get('1', {}).get('busy')}")
        print(f"   Tasks in Queue:")
        for task in queue_status.get('queue', []):
            print(f"      - {task.get('task_id')}")
    
    # Monitor for 10 seconds
    print("\n⏱️  Monitoring queue for 10 seconds...")
    for i in range(10):
        time.sleep(1)
        queue_status = check_queue()
        if queue_status:
            queue_size = queue_status.get('queue_size', 0)
            gpu0_busy = queue_status.get('gpus', {}).get('0', {}).get('busy', False)
            gpu1_busy = queue_status.get('gpus', {}).get('1', {}).get('busy', False)
            print(f"   [{i+1}s] Queue: {queue_size}, GPU0: {'🔴' if gpu0_busy else '🟢'}, GPU1: {'🔴' if gpu1_busy else '🟢'}")

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print(" 🧪 Atomic GPU Reservation Test Suite")
    print("="*80)
    print(f" API: {API_URL}")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Check server health
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is healthy\n")
        else:
            print(f"⚠️  Server returned status {response.status_code}\n")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Please start the server with: python3 app.py")
        return
    
    # Run tests
    test_single_request()
    time.sleep(3)
    
    test_concurrent_2_requests()
    time.sleep(3)
    
    test_queue_overflow()
    
    print("\n" + "="*80)
    print(" ✅ All tests completed!")
    print("="*80)
    print("\nIMPORTANT: Check the server logs to verify:")
    print("  1. GPU is reserved BEFORE TTS generation")
    print("  2. TTS port matches the reserved GPU")
    print("  3. Queue processes tasks as GPUs become free")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
