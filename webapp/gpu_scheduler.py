#!/usr/bin/env python3
"""
Simple GPU Scheduler - 1 GPU = 1 Video
Total 3 videos parallel processing
"""
import requests
import json
import time
import subprocess
import os
import threading
from datetime import datetime
from queue import Queue
from typing import Dict, Optional

class SimpleGPUScheduler:
    def __init__(self):
        # 1 task per GPU - simple!
        self.gpu_config = {
            0: {"port": 8390, "busy": False},
            1: {"port": 8391, "busy": False},
            2: {"port": 8392, "busy": False}
        }
        self.task_queue = []  # FIFO queue
        self.active_tasks = {}  # {task_id: {gpu_id, status, start_time}}
        self.completed_tasks = []
        self.lock = threading.Lock()
        
    def find_available_gpu(self) -> Optional[int]:
        """
        Find first free GPU
        Returns: GPU ID (0, 1, or 2) or None if all busy
        """
        with self.lock:
            for gpu_id in [0, 1, 2]:
                if not self.gpu_config[gpu_id]["busy"]:
                    return gpu_id
        return None
    
    def get_gpu_status(self) -> Dict:
        """Get status of all GPUs"""
        with self.lock:
            return {
                "gpu0": "busy" if self.gpu_config[0]["busy"] else "free",
                "gpu1": "busy" if self.gpu_config[1]["busy"] else "free",
                "gpu2": "busy" if self.gpu_config[2]["busy"] else "free",
                "queue_size": len(self.task_queue),
                "active_tasks": len([t for t in self.active_tasks.values() if t["status"] == "running"]),
                "completed": len(self.completed_tasks)
            }
    
    def submit_to_gpu(self, video_path: str, audio_path: str, task_id: str, gpu_id: int) -> bool:
        """Submit video generation task to specific GPU"""
        port = self.gpu_config[gpu_id]["port"]
        # GPU containers mount ~/heygem_data/gpu{id} to /code/data
        gpu_data_dir = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/face2face/")
        
        # Copy files to GPU directory
        os.makedirs(gpu_data_dir, exist_ok=True)
        try:
            subprocess.run(['cp', video_path, gpu_data_dir], check=True)
            subprocess.run(['cp', audio_path, gpu_data_dir], check=True)
        except Exception as e:
            print(f"❌ File copy error: {e}")
            return False
        
        # Submit to HeyGem API
        payload = {
            "audio_url": f"/code/data/face2face/{os.path.basename(audio_path)}",
            "video_url": f"/code/data/face2face/{os.path.basename(video_path)}",
            "code": task_id,
            "chaofen": 1,
            "watermark_switch": 0,
            "pn": 1
        }
        
        try:
            print(f"🚀 Submitting to GPU {gpu_id} on port {port}")
            print(f"   Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                f"http://127.0.0.1:{port}/easy/submit",
                json=payload,
                timeout=30
            )
            
            print(f"   Response Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
            result = response.json()
            
            if result.get('success'):
                with self.lock:
                    self.gpu_config[gpu_id]["busy"] = True
                print(f"✅ Task '{task_id}' → GPU {gpu_id} (Port {port})")
                return True
            else:
                print(f"❌ Submission failed: {result}")
                return False
                
        except Exception as e:
            print(f"❌ API error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def monitor_task(self, task_id: str, gpu_id: int, video_path: str, audio_path: str):
        """Monitor task until completion"""
        port = self.gpu_config[gpu_id]["port"]
        # Output is written to /code/data/temp/ inside container -> ~/heygem_data/gpu{id}/temp/ on host
        output_file = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/temp/{task_id}-r.mp4")
        start_time = time.time()
        
        print(f"🔍 Monitoring task '{task_id}' on GPU {gpu_id}")
        print(f"   Watching for: {output_file}")
        
        while True:
            if os.path.exists(output_file):
                # Wait for file to be completely written by checking size stability
                prev_size = 0
                stable_count = 0
                
                print(f"   ⏳ Waiting for file completion...")
                while stable_count < 3:  # Need 3 consecutive stable checks
                    time.sleep(2)
                    current_size = os.path.getsize(output_file)
                    
                    if current_size == prev_size and current_size > 10000:
                        stable_count += 1
                    else:
                        stable_count = 0
                        prev_size = current_size
                
                print(f"   📁 File stable: {current_size/1024/1024:.1f} MB")
                
                if current_size > 10000:  # Valid file size
                    elapsed = time.time() - start_time
                    
                    # Copy to outputs directory
                    output_name = f"output_{task_id}.mp4"
                    output_dest = f"/nvme0n1-disk/HeyGem/webapp/outputs/{output_name}"
                    subprocess.run(['cp', output_file, output_dest])
                    
                    # Update status
                    with self.lock:
                        self.gpu_config[gpu_id]["busy"] = False
                        self.active_tasks[task_id]["status"] = "completed"
                        self.active_tasks[task_id]["elapsed"] = elapsed
                        self.active_tasks[task_id]["output"] = output_name
                        self.completed_tasks.append({
                            "task_id": task_id,
                            "gpu_id": gpu_id,
                            "elapsed": elapsed,
                            "output": output_name
                        })
                    
                    print(f"✅ '{task_id}' completed on GPU {gpu_id} ({elapsed/60:.1f} mins)")
                    
                    # Process next task in queue
                    self.process_next_in_queue()
                    break
            
            time.sleep(5)
    
    def add_task(self, video_path: str, audio_path: str, text: str = "", task_id: str = None):
        """Add task to queue"""
        if task_id is None:
            task_id = f"task_{int(time.time())}"
        
        task = {
            "task_id": task_id,
            "video_path": video_path,
            "audio_path": audio_path,
            "text": text,
            "status": "queued",
            "queued_at": time.time()
        }
        
        with self.lock:
            self.task_queue.append(task)
        
        print(f"📝 Task added: {task_id} (Queue: {len(self.task_queue)})")
        
        # Try to process immediately
        self.process_next_in_queue()
        
        return task_id
    
    def process_next_in_queue(self):
        """Process next task if GPU available"""
        gpu_id = self.find_available_gpu()
        
        if gpu_id is None:
            return  # All GPUs busy
        
        with self.lock:
            if not self.task_queue:
                return  # Queue empty
            
            task = self.task_queue.pop(0)  # FIFO
        
        task_id = task["task_id"]
        
        # Submit to GPU
        success = self.submit_to_gpu(
            task["video_path"],
            task["audio_path"],
            task_id,
            gpu_id
        )
        
        if success:
            # Start monitoring in background
            monitor_thread = threading.Thread(
                target=self.monitor_task,
                args=(task_id, gpu_id, task["video_path"], task["audio_path"]),
                daemon=True
            )
            monitor_thread.start()
            
            # Track active task
            with self.lock:
                self.active_tasks[task_id] = {
                    "gpu_id": gpu_id,
                    "status": "running",
                    "start_time": time.time(),
                    "video": task["video_path"],
                    "audio": task["audio_path"],
                    "text": task.get("text", "")
                }
        else:
            # Re-queue on failure
            with self.lock:
                self.task_queue.insert(0, task)
    
    def get_task_status(self, task_id: str) -> Dict:
        """Get status of specific task"""
        with self.lock:
            # Check if active
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if task["status"] == "running":
                    elapsed = time.time() - task["start_time"]
                    return {
                        "status": "running",
                        "gpu_id": task["gpu_id"],
                        "elapsed_seconds": int(elapsed),
                        "estimated_remaining": max(0, 300 - int(elapsed))  # ~5 min estimate
                    }
                elif task["status"] == "completed":
                    return {
                        "status": "completed",
                        "gpu_id": task["gpu_id"],
                        "elapsed_seconds": int(task["elapsed"]),
                        "output": task.get("output", "")
                    }
            
            # Check if in queue
            for task in self.task_queue:
                if task["task_id"] == task_id:
                    position = self.task_queue.index(task) + 1
                    return {
                        "status": "queued",
                        "queue_position": position
                    }
            
            return {"status": "not_found"}


# Global scheduler instance
scheduler = SimpleGPUScheduler()


if __name__ == "__main__":
    print("🚀 Simple GPU Scheduler - 1 GPU = 1 Video")
    print("=" * 80)
    print("3 GPUs available for parallel processing")
    print("=" * 80)
