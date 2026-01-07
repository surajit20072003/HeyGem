#!/usr/bin/env python3
"""
Better test - Track GPU states during processing
"""
import sys
sys.path.insert(0, '/nvme0n1-disk/nvme01/HeyGem/webapp')

# Reload module
import importlib
import gpu_scheduler
importlib.reload(gpu_scheduler)
from gpu_scheduler import scheduler

import time

print("=" * 80)
print("✅ DETAILED GPU STATE TRACKING TEST")
print("=" * 80)

# Reset
with scheduler.lock:
    scheduler.task_queue.clear()
    scheduler.active_tasks.clear()
    for gpu_id in [0, 1, 2]:
        scheduler.gpu_config[gpu_id]["busy"] = False

# Add 3 tasks
print("\n1️⃣ Adding 3 tasks:")
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

with scheduler.lock:
    print(f"   Queue size: {len(scheduler.task_queue)}")
    print(f"   Tasks in queue: {[t['task_id'] for t in scheduler.task_queue]}")

print("\n2️⃣ First process_next_in_queue() call:")
with scheduler.lock:
    print(f"   BEFORE: Queue={len(scheduler.task_queue)}, Busy GPUs={[g for g in [0,1,2] if scheduler.gpu_config[g]['busy']]}")

# Mock submit to just track assignment
calls = []
def mock_submit(video, audio, tid, gid):
    calls.append((tid, gid))
    print(f"      submit_to_gpu called: task={tid}, gpu={gid}")
    return False  # Fail so GPU gets freed

original = scheduler.submit_to_gpu
scheduler.submit_to_gpu = mock_submit

scheduler.process_next_in_queue()

scheduler.submit_to_gpu = original

with scheduler.lock:
    print(f"   AFTER:  Queue={len(scheduler.task_queue)}, Busy GPUs={[g for g in [0,1,2] if scheduler.gpu_config[g]['busy']]}")
    print(f"   Tasks in queue: {[t['task_id'] for t in scheduler.task_queue]}")

print(f"\n3️⃣ Submit calls made: {calls}")
print(f"   Expected: 1 call")
print(f"   Actual: {len(calls)} call(s)")

# Cleanup
with scheduler.lock:
    scheduler.task_queue.clear()

print("=" * 80)
