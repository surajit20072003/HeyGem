#!/usr/bin/env python3
"""
Quick Start Guide: Add Your Videos Here
Edit the 'tasks' list below with your video/audio file paths
"""
from smart_gpu_scheduler import GPUScheduler
import time

def main():
    scheduler = GPUScheduler()
    
    # Unique timestamp to avoid cache
    timestamp = int(time.time())
    
    print("🚀 Smart GPU Scheduler - 6 Parallel Videos")
    print("="*80)
    
    # ========================================
    # 📝 EDIT THIS SECTION - Add Your Videos
    # ========================================
    tasks = [
        # Task 1
        {
            "video": "/nvme0n1-disk/HeyGem/input_video02.mp4",      # <-- Your video path
            "audio": "/nvme0n1-disk/HeyGem/modi.wav",     # <-- Your audio path
            "name": f"video1_{timestamp}"                         # <-- Unique name
        },
        
        # Task 2
        {
            "video": "/nvme0n1-disk/HeyGem/input_video02.mp4",
            "audio": "/nvme0n1-disk/HeyGem/modi.wav",
            "name": f"video2_{timestamp}"
        },
        
        # Task 3
        {
            "video": "/nvme0n1-disk/HeyGem/input_video02.mp4",
            "audio": "/nvme0n1-disk/HeyGem/modi.wav",
            "name": f"video3_{timestamp}"
        },
        
        # Task 4
        {
            "video": "/nvme0n1-disk/HeyGem/input_video02.mp4",
            "audio": "/nvme0n1-disk/HeyGem/modi.wav",
            "name": f"video4_{timestamp}"
        },
        
        # Task 5
        {
            "video": "/nvme0n1-disk/HeyGem/input_video02.mp4",
            "audio": "/nvme0n1-disk/HeyGem/modi.wav",
            "name": f"video5_{timestamp}"
        },
        
        # Task 6
        {
            "video": "/nvme0n1-disk/HeyGem/input_video02.mp4",
            "audio": "/nvme0n1-disk/HeyGem/modi.wav",
            "name": f"video6_{timestamp}"
        }
    ]
    # ========================================
    # End of configuration
    # ========================================
    
    # Verify files
    import os
    print("\n📁 Checking files...")
    valid_tasks = []
    for i, task in enumerate(tasks, 1):
        v_exists = os.path.exists(task["video"])
        a_exists = os.path.exists(task["audio"])
        if v_exists and a_exists:
            valid_tasks.append(task)
            print(f"  ✅ Task {i} ({task['name']}): Ready")
        else:
            print(f"  ❌ Task {i} ({task['name']}): Missing files!")
            if not v_exists:
                print(f"     Video not found: {task['video']}")
            if not a_exists:
                print(f"     Audio not found: {task['audio']}")
    
    if not valid_tasks:
        print("\n❌ No valid tasks found! Please check file paths.")
        return
    
    print(f"\n✅ {len(valid_tasks)} tasks ready to process")
    print("\n" + "="*80)
    print("🔄 GPU Assignment Strategy:")
    print("   GPU 0 (Port 8390): Will handle 2 tasks")
    print("   GPU 1 (Port 8391): Will handle 2 tasks")
    print("   GPU 2 (Port 8392): Will handle 2 tasks")
    print("   Total: 6 parallel videos")
    print("="*80 + "\n")
    
    # Add to queue
    for task in valid_tasks:
        scheduler.add_video_task(video_file=task["video"], 
                                audio_file=task["audio"], 
                                task_name=task["name"])
    
    # Process
    print("🚀 Starting processing...")
    scheduler.process_queue()
    scheduler.wait_for_completion()
    
    print("\n✅ Done! Check outputs:")
    for task in valid_tasks:
        print(f"   � output_{task['name']}.mp4")


if __name__ == "__main__":
    main()
