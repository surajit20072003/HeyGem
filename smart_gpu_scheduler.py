#!/usr/bin/env python3
"""
Intelligent GPU Scheduler for HeyGem
Handles up to 6 parallel videos (2 per GPU) with smart GPU selection
"""
import requests
import json
import time
import subprocess
import os
import threading
from datetime import datetime
from queue import Queue
from typing import List, Dict, Tuple

class GPUScheduler:
    def __init__(self):
        self.gpu_config = {
            0: {"port": 8390, "max_tasks": 2, "current_tasks": 0},
            1: {"port": 8391, "max_tasks": 2, "current_tasks": 0},
            2: {"port": 8392, "max_tasks": 2, "current_tasks": 0}
        }
        self.task_queue = Queue()
        self.active_tasks = {}  # {task_code: {gpu_id, thread, status}}
        self.completed_tasks = []
        self.lock = threading.Lock()
        
    def get_gpu_memory(self, gpu_id: int) -> Dict:
        """Get current GPU memory usage"""
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=index,memory.used,memory.total',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, check=True)
            
            for line in result.stdout.strip().split('\n'):
                parts = [x.strip() for x in line.split(',')]
                if int(parts[0]) == gpu_id:
                    return {
                        "gpu_id": gpu_id,
                        "used_mb": int(parts[1]),
                        "total_mb": int(parts[2]),
                        "used_gb": round(int(parts[1]) / 1024, 2),
                        "available_gb": round((int(parts[2]) - int(parts[1])) / 1024, 2)
                    }
        except Exception as e:
            print(f"⚠️  GPU stats error: {e}")
        return {}
    
    def find_available_gpu(self) -> int:
        """
        Find first available GPU with free slot
        Priority: GPU 0 -> GPU 1 -> GPU 2
        Returns: GPU ID or -1 if all full
        """
        with self.lock:
            for gpu_id in [0, 1, 2]:  # Priority order
                config = self.gpu_config[gpu_id]
                if config["current_tasks"] < config["max_tasks"]:
                    # Check actual memory availability
                    mem = self.get_gpu_memory(gpu_id)
                    if mem.get("available_gb", 0) > 10:  # Need at least 10GB free
                        return gpu_id
        return -1
    
    def submit_task(self, video_file: str, audio_file: str, task_code: str, gpu_id: int):
        """Submit task to specific GPU"""
        # Copy files to GPU data directory
        gpu_data_dir = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/face2face/")
        os.makedirs(gpu_data_dir, exist_ok=True)
        
        try:
            subprocess.run(['cp', video_file, gpu_data_dir], check=True)
            subprocess.run(['cp', audio_file, gpu_data_dir], check=True)
        except Exception as e:
            print(f"❌ File copy error: {e}")
            return False
        
        # Submit to GPU
        port = self.gpu_config[gpu_id]["port"]
        payload = {
            "audio_url": f"/code/data/face2face/{os.path.basename(audio_file)}",
            "video_url": f"/code/data/face2face/{os.path.basename(video_file)}",
            "code": task_code,
            "chaofen": 0,
            "watermark_switch": 0,
            "pn": 1
        }
        
        try:
            response = requests.post(
                f"http://127.0.0.1:{port}/easy/submit",
                json=payload,
                timeout=30
            )
            result = response.json()
            if result.get('success'):
                with self.lock:
                    self.gpu_config[gpu_id]["current_tasks"] += 1
                print(f"✅ Task {task_code} submitted to GPU {gpu_id} (Port {port})")
                return True
            else:
                print(f"❌ Submission failed: {result}")
                return False
        except Exception as e:
            print(f"❌ API error: {e}")
            return False
    
    def monitor_task(self, task_code: str, gpu_id: int, video_file: str, audio_file: str):
        """Monitor task until completion"""
        port = self.gpu_config[gpu_id]["port"]
        output_file = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/temp/{task_code}-r.mp4")
        
        start_time = time.time()
        
        while True:
            # Check if output file exists
            if os.path.exists(output_file):
                time.sleep(3)  # Wait for write completion
                
                # Verify file size
                if os.path.getsize(output_file) > 1000:  # At least 1KB
                    elapsed = time.time() - start_time
                    
                    # Copy to main directory
                    output_name = f"output_{task_code}.mp4"
                    subprocess.run([
                        'cp', output_file,
                        f"/nvme0n1-disk/HeyGem/{output_name}"
                    ])
                    
                    # Update status
                    with self.lock:
                        self.gpu_config[gpu_id]["current_tasks"] -= 1
                        self.active_tasks[task_code]["status"] = "completed"
                        self.active_tasks[task_code]["elapsed"] = elapsed
                        self.completed_tasks.append({
                            "task_code": task_code,
                            "gpu_id": gpu_id,
                            "elapsed": elapsed,
                            "output": output_name,
                            "video": os.path.basename(video_file),
                            "audio": os.path.basename(audio_file)
                        })
                    
                    print(f"✅ [{task_code}] Completed on GPU {gpu_id} in {elapsed/60:.1f} mins")
                    break
            
            time.sleep(5)
    
    def add_video_task(self, video_file: str, audio_file: str, task_name: str = None):
        """Add video to processing queue"""
        if task_name is None:
            task_name = f"task_{int(time.time())}_{len(self.active_tasks)}"
        
        self.task_queue.put({
            "video": video_file,
            "audio": audio_file,
            "code": task_name
        })
        print(f"📝 Added to queue: {task_name}")
    
    def process_queue(self):
        """Process queue and assign tasks to available GPUs"""
        while not self.task_queue.empty():
            # Find available GPU
            gpu_id = self.find_available_gpu()
            
            if gpu_id == -1:
                print("⏳ All GPUs busy, waiting...")
                time.sleep(10)
                continue
            
            # Get next task from queue
            task = self.task_queue.get()
            task_code = task["code"]
            
            # Submit task
            success = self.submit_task(
                task["video"],
                task["audio"],
                task_code,
                gpu_id
            )
            
            if success:
                # Start monitoring thread
                monitor_thread = threading.Thread(
                    target=self.monitor_task,
                    args=(task_code, gpu_id, task["video"], task["audio"])
                )
                monitor_thread.daemon = True
                monitor_thread.start()
                
                # Track task
                with self.lock:
                    self.active_tasks[task_code] = {
                        "gpu_id": gpu_id,
                        "thread": monitor_thread,
                        "status": "running",
                        "start_time": time.time(),
                        "video": task["video"],
                        "audio": task["audio"]
                    }
                
                time.sleep(2)  # Small delay between submissions
            else:
                # Re-queue on failure
                self.task_queue.put(task)
                time.sleep(5)
        
        print("\n✅ All tasks submitted! Waiting for completion...")
    
    def show_status(self):
        """Display current GPU and task status"""
        print("\n" + "="*80)
        print("📊 GPU STATUS")
        print("="*80)
        
        for gpu_id in [0, 1, 2]:
            config = self.gpu_config[gpu_id]
            mem = self.get_gpu_memory(gpu_id)
            print(f"GPU {gpu_id}: {config['current_tasks']}/{config['max_tasks']} tasks | "
                  f"{mem.get('used_gb', 0):.1f}/{mem.get('total_mb', 0)/1024:.1f} GB | "
                  f"Port {config['port']}")
        
        print("\n📋 ACTIVE TASKS:")
        with self.lock:
            if not self.active_tasks:
                print("   None")
            for code, info in self.active_tasks.items():
                if info["status"] == "running":
                    elapsed = time.time() - info["start_time"]
                    print(f"   {code}: GPU {info['gpu_id']} | {elapsed/60:.1f} mins")
        
        print(f"\n✅ COMPLETED: {len(self.completed_tasks)}")
        print("="*80)
    
    def wait_for_completion(self):
        """Wait for all tasks to complete"""
        while True:
            with self.lock:
                running = sum(1 for t in self.active_tasks.values() if t["status"] == "running")
            
            if running == 0:
                break
            
            self.show_status()
            time.sleep(15)
        
        print("\n🎉 ALL TASKS COMPLETED!")
        self.print_summary()
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*80)
        print("📊 FINAL SUMMARY")
        print("="*80)
        
        for task in self.completed_tasks:
            print(f"✅ {task['task_code']}")
            print(f"   GPU: {task['gpu_id']} | Time: {task['elapsed']/60:.1f} mins")
            print(f"   Video: {task['video']} | Audio: {task['audio']}")
            print(f"   Output: {task['output']}\n")
        
        if self.completed_tasks:
            avg_time = sum(t['elapsed'] for t in self.completed_tasks) / len(self.completed_tasks)
            total_time = max(t['elapsed'] for t in self.completed_tasks)
            print(f"Average time per video: {avg_time/60:.1f} minutes")
            print(f"Total wall-clock time: {total_time/60:.1f} minutes")
            print(f"Efficiency gain: {len(self.completed_tasks)}x faster than sequential")
        
        print("="*80)


def main():
    """Example usage"""
    scheduler = GPUScheduler()
    
    # Example: Add 6 videos to process
    print("🚀 Starting Intelligent GPU Scheduler")
    print("="*80)
    
    # Add your video tasks here
    # scheduler.add_video_task("/nvme0n1-disk/HeyGem/input_video.mp4", 
    #                          "/nvme0n1-disk/HeyGem/input_audio.mp3",
    #                          "video1")
    
    # For testing, uncomment and add your files:
    # scheduler.add_video_task("video1.mp4", "audio1.mp3", "task_1")
    # scheduler.add_video_task("video2.mp4", "audio2.mp3", "task_2")
    # ... up to 6 tasks
    
    print(f"\n📝 Queue size: {scheduler.task_queue.qsize()} tasks")
    print("🔄 Starting processing...")
    
    # Start processing
    scheduler.process_queue()
    
    # Wait for completion
    scheduler.wait_for_completion()


if __name__ == "__main__":
    main()
