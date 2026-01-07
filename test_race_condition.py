#!/usr/bin/env python3
"""
Demonstrate Race Condition in GPU Assignment
"""
import sys
sys.path.insert(0, '/nvme0n1-disk/nvme01/HeyGem/webapp')

from gpu_scheduler import scheduler
import threading
import time

print("=" * 80)
print("🐛 RACE CONDITION DEMONSTRATION")
print("=" * 80)

# Add 3 tasks quickly
def add_dummy_task(task_num):
    """Simulate adding a task"""
    task_id = f"test_task_{task_num}"
    video = "/tmp/dummy.mp4"
    audio = "/tmp/dummy.wav"
    
    task = {
        "task_id": task_id,
        "video_path": video,
        "audio_path": audio,
        "text": f"Task {task_num}",
        "tts_duration": 0.0,
        "status": "queued",
        "queued_at": time.time()
    }
    
    with scheduler.lock:
        scheduler.task_queue.append(task)
    print(f"   Added {task_id} to queue")

# Add 3 tasks
print("\n1️⃣ Adding 3 tasks to queue:")
for i in range(1, 4):
    add_dummy_task(i)

print(f"\n2️⃣ Queue size: {len(scheduler.task_queue)}")

# Now call process_next_in_queue from 3 threads simultaneously
print("\n3️⃣ Simulating concurrent processing (3 threads):")
print("   This will demonstrate the race condition...")

results = []

def test_process():
    """Wrapper to capture which GPU is selected"""
    gpu_id = scheduler.find_available_gpu()
    results.append(gpu_id)
    print(f"   Thread {threading.current_thread().name}: Got GPU {gpu_id}")
    time.sleep(0.1)  # Small delay to let all threads run

threads = []
for i in range(3):
    t = threading.Thread(target=test_process, name=f"T{i}")
    threads.append(t)

# Start all threads at once
for t in threads:
    t.start()

# Wait for completion
for t in threads:
    t.join()

print(f"\n4️⃣ Results:")
print(f"   GPUs assigned: {results}")
print(f"   Expected: [0, 1, 2] (one GPU per thread)")
print(f"   Actual: {results}")

if results == [0, 0, 0]:
    print("\n   ⚠️  BUG CONFIRMED: All threads got GPU 0!")
    print("   This is the RACE CONDITION causing only GPU 0 to be used.")
else:
    print("\n   ✅ No race condition detected (all got same free GPU)")

# Cleanup
with scheduler.lock:
    scheduler.task_queue.clear()

print("=" * 80)
