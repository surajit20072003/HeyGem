#!/usr/bin/env python3
"""
Test GPU Scheduler Logic
"""
import sys
sys.path.insert(0, '/nvme0n1-disk/nvme01/HeyGem/webapp')

from gpu_scheduler import scheduler

print("=" * 80)
print("🔍 GPU Scheduler Diagnostic Test")
print("=" * 80)

# Check current GPU status
print("\n1️⃣ Current GPU Status:")
status = scheduler.get_gpu_status()
for key, value in status.items():
    print(f"   {key}: {value}")

# Check GPU config
print("\n2️⃣ GPU Configuration:")
with scheduler.lock:
    for gpu_id, config in scheduler.gpu_config.items():
        print(f"   GPU {gpu_id}: Port={config['port']}, Busy={config['busy']}")

# Test find_available_gpu
print("\n3️⃣ Testing find_available_gpu():")
for i in range(5):
    available = scheduler.find_available_gpu()
    print(f"   Attempt {i+1}: Available GPU = {available}")

# Check queue
print("\n4️⃣ Task Queue Status:")
with scheduler.lock:
    print(f"   Queue length: {len(scheduler.task_queue)}")
    print(f"   Active tasks: {len(scheduler.active_tasks)}")
    for task_id, task_data in scheduler.active_tasks.items():
        print(f"      Task {task_id}: GPU={task_data.get('gpu_id')}, Status={task_data.get('status')}")

# Check if GPUs are stuck in busy state
print("\n5️⃣ Checking for stuck GPUs:")
with scheduler.lock:
    for gpu_id in [0, 1, 2]:
        is_busy = scheduler.gpu_config[gpu_id]["busy"]
        # Check if there's actually a task running on this GPU
        tasks_on_gpu = [t for t_id, t in scheduler.active_tasks.items() 
                       if t.get('gpu_id') == gpu_id and t.get('status') == 'running']
        
        if is_busy and len(tasks_on_gpu) == 0:
            print(f"   ⚠️  GPU {gpu_id} is marked BUSY but has NO running tasks (STUCK!)")
        elif is_busy and len(tasks_on_gpu) > 0:
            print(f"   ✅ GPU {gpu_id} is busy with task: {tasks_on_gpu[0]}")
        else:
            print(f"   🟢 GPU {gpu_id} is FREE")

print("\n" + "=" * 80)
