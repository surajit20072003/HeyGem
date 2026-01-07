#!/usr/bin/env python3
"""
Test the FIXED GPU Assignment Logic
"""
import sys
sys.path.insert(0, '/nvme0n1-disk/nvme01/HeyGem/webapp')

# Reload module to get latest changes
import importlib
import gpu_scheduler
importlib.reload(gpu_scheduler)
from gpu_scheduler import scheduler

import threading
import time

print("=" * 80)
print("✅ TESTING FIXED GPU ASSIGNMENT LOGIC")
print("=" * 80)

# Reset scheduler state
with scheduler.lock:
    scheduler.task_queue.clear()
    scheduler.active_tasks.clear()
    for gpu_id in [0, 1, 2]:
        scheduler.gpu_config[gpu_id]["busy"] = False

# Create dummy files for testing
import os
os.makedirs('/tmp/test_videos', exist_ok=True)
with open('/tmp/test_videos/dummy.mp4', 'w') as f:
    f.write("dummy video")
with open('/tmp/test_videos/dummy.wav', 'w') as f:
    f.write("dummy audio")

# Manually add 3 tasks to the queue
print("\n1️⃣ Adding 3 tasks to queue:")
for i in range(1, 4):
    task_id = f"test_task_{i}"
    task = {
        "task_id": task_id,
        "video_path": "/tmp/test_videos/dummy.mp4",
        "audio_path": "/tmp/test_videos/dummy.wav",
        "text": f"Task {i}",
        "tts_duration": 0.0,
        "status": "queued",
        "queued_at": time.time()
    }
    with scheduler.lock:
        scheduler.task_queue.append(task)
    print(f"   ✅ Added {task_id}")

print(f"\n2️⃣ Queue size: {len(scheduler.task_queue)}")
print(f"   Initial GPU states: All FREE")

# Call process_next_in_queue 3 times in rapid succession (simulating concurrent requests)
print("\n3️⃣ Processing tasks with FIXED logic:")

assigned_gpus = []

# Override submit_to_gpu to prevent actual API calls and just track GPU assignments
original_submit = scheduler.submit_to_gpu
def mock_submit(video_path, audio_path, task_id, gpu_id):
    assigned_gpus.append(gpu_id)
    print(f"   📌 Task {task_id} → GPU {gpu_id}")
    # Return False so it doesn't start monitoring (which would free the GPU)
    return False

scheduler.submit_to_gpu = mock_submit

# Process all queued tasks
for i in range(3):
    scheduler.process_next_in_queue()
    time.sleep(0.01)  # Tiny delay

# Restore original function
scheduler.submit_to_gpu = original_submit

print(f"\n4️⃣ Results:")
print(f"   GPUs assigned: {assigned_gpus}")
print(f"   Expected: 3 different GPUs (e.g., [0, 1, 2])")

# Check GPU states
with scheduler.lock:
    busy_count = sum(1 for gid in [0, 1, 2] if scheduler.gpu_config[gid]["busy"])
    print(f"   GPUs marked as busy: {busy_count}")

if len(set(assigned_gpus)) == 3:
    print("\n   🎉 SUCCESS: All 3 tasks got DIFFERENT GPUs!")
    print("   ✅ Race condition FIXED!")
else:
    print(f"\n   ❌ FAILED: Tasks were assigned to: {assigned_gpus}")
    print("   Some GPUs got multiple tasks (race condition still exists)")

# Cleanup
with scheduler.lock:
    scheduler.task_queue.clear()
    for gpu_id in [0, 1, 2]:
        scheduler.gpu_config[gpu_id]["busy"] = False

print("=" * 80)
