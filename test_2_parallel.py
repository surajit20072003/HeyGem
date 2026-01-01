#!/usr/bin/env python3
"""
SIMPLEST EXAMPLE - Test with 2 videos first
"""
from smart_gpu_scheduler import GPUScheduler

scheduler = GPUScheduler()

# Add 2 videos to test (will both go to GPU 0)
scheduler.add_video_task(
    video_file="/nvme0n1-disk/HeyGem/input_video.mp4",
    audio_file="/nvme0n1-disk/HeyGem/input_audio.mp3",
    task_name="test_video_1"
)

scheduler.add_video_task(
    video_file="/nvme0n1-disk/HeyGem/input_video02.mp4",
    audio_file="/nvme0n1-disk/HeyGem/input_audio.mp3",
    task_name="test_video_2"
)

print("✅ 2 tasks added - both will run on GPU 0 simultaneously")
print("⏱️  This tests if 2 parallel tasks work without OOM")

scheduler.process_queue()
scheduler.wait_for_completion()
