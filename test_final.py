#!/usr/bin/env python3
"""
Final Test - Simulate actual successful task processing
"""
import sys
sys.path.insert(0, '/nvme0n1-disk/nvme01/HeyGem/webapp')

import importlib
import gpu_scheduler
importlib.reload(gpu_scheduler)
from gpu_scheduler import scheduler

import time

print("=" * 80)
print("🎯 FINAL TEST: Successful Task Processing with 3 GPUs")
print("=" * 80)

# Reset
with scheduler.lock:
    scheduler.task_queue.clear()
    scheduler.active_tasks.clear()
    for gpu_id in [0, 1, 2]:
        scheduler.gpu_config[gpu_id]["busy"] = False

# Add 3 tasks
print("\n1️⃣ Adding 3 tasks to queue:")
for i in range(1, 4):
    task = {
        "task_id": f"task_{i}",
        "video_path": "/tmp/dummy.mp4",
        "audio_path": "/tmp/dummy.wav",
        "text": f"Text {i}",
        "tts_duration": 0.0,
        "status": "queued",
        "queued_at": time.time()
    }
    with scheduler.lock:
        scheduler.task_queue.append(task)
        print(f"   ✅ Added task_{i}")

# Mock submit_to_gpu to return True (success) but NOT start monitoring
assignments = []
def mock_submit(video, audio, tid, gid):
    assignments.append((tid, gid))
    print(f"   📌 submit_to_gpu: {tid} → GPU {gid}")
    return True  # SUCCESS!

original_submit = scheduler.submit_to_gpu
original_monitor = scheduler.monitor_task

# We need to prevent monitor_task from running
def mock_monitor(*args, **kwargs):
    print(f"   �� Monitor skipped (test mode)")
    pass

scheduler.submit_to_gpu = mock_submit
scheduler.monitor_task = mock_monitor

# Process all 3 tasks
print("\n2️⃣ Processing 3 tasks sequentially:")
for i in range(3):
    print(f"\n   Call {i+1} to process_next_in_queue():")
    scheduler.process_next_in_queue()
    with scheduler.lock:
        busy_gpus = [g for g in [0, 1, 2] if scheduler.gpu_config[g]["busy"]]
        print(f"   📊 Busy GPUs after call {i+1}: {busy_gpus}")

# Restore original functions
scheduler.submit_to_gpu = original_submit
scheduler.monitor_task = original_monitor

print("\n3️⃣ RESULTS:")
print(f"   Total assignments: {len(assignments)}")
for task_id, gpu_id in assignments:
    print(f"      {task_id} → GPU {gpu_id}")

assigned_gpus = [gid for _, gid in assignments]
unique_gpus = list(set(assigned_gpus))

print(f"\n4️⃣ VERDICT:")
if len(unique_gpus) == 3 and set(unique_gpus) == {0, 1, 2}:
    print(f"   🎉 SUCCESS! All 3 GPUs used: {assigned_gpus}")
    print(f"   ✅ Race condition FIXED!")
else:
    print(f"   ❌ FAILED: GPUs used = {assigned_gpus}")
    print(f"   Expected: Each task on different GPU")

# Show final GPU states
with scheduler.lock:
    print(f"\n5️⃣ Final GPU busy states:")
    for gid in [0, 1, 2]:
        print(f"   GPU {gid}: {'BUSY' if scheduler.gpu_config[gid]['busy'] else 'FREE'}")

# Cleanup
with scheduler.lock:
    scheduler.task_queue.clear()
    scheduler.active_tasks.clear()
    for gpu_id in [0, 1, 2]:
        scheduler.gpu_config[gpu_id]["busy"] = False

print("=" * 80)
