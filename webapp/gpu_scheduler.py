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
        self.pre_processing_tasks = {} # {task_id: "status_message"}
        self.completed_tasks = []
        self.lock = threading.Lock()

    def get_gpu_memory(self, gpu_id: int) -> str:
        """Get current GPU memory usage via nvidia-smi (returns string '1234 MiB')"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits', '-i', str(gpu_id)],
                capture_output=True, text=True
            )
            return f"{result.stdout.strip()} MiB"
        except Exception:
            return "0 MiB"
        
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
                "gpu0": {"status": "busy" if self.gpu_config[0]["busy"] else "free", "memory": self.get_gpu_memory(0)},
                "gpu1": {"status": "busy" if self.gpu_config[1]["busy"] else "free", "memory": self.get_gpu_memory(1)},
                "gpu2": {"status": "busy" if self.gpu_config[2]["busy"] else "free", "memory": self.get_gpu_memory(2)},
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
                # GPU is already marked busy by process_next_in_queue
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
        """Monitor task until completion with timeout and failure detection"""
        port = self.gpu_config[gpu_id]["port"]
        # Output is written to /code/data/temp/ inside container -> ~/heygem_data/gpu{id}/temp/ on host
        output_file = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/temp/{task_id}-r.mp4")
        start_time = time.time()
        
        # NEW: Add timeout (10 minutes max)
        MAX_WAIT_TIME = 3600
        CHECK_INTERVAL = 5   # Check GPU API every 5 seconds
        
        print(f"🔍 Monitoring task '{task_id}' on GPU {gpu_id}")
        print(f"   Watching for: {output_file}")
        print(f"   Timeout: {MAX_WAIT_TIME}s")
        
        max_memory = 0 # Track peak usage
        last_api_check = 0
        
        while True:
            elapsed = time.time() - start_time
            
            # NEW: Check timeout
            if elapsed > MAX_WAIT_TIME:
                print(f"⏰ TIMEOUT: Task '{task_id}' exceeded {MAX_WAIT_TIME}s")
                with self.lock:
                    self.gpu_config[gpu_id]["busy"] = False
                    print(f"🟢 GPU {gpu_id} FREED (timeout)")
                    self.active_tasks[task_id]["status"] = "failed"
                    self.active_tasks[task_id]["error"] = f"Timeout after {MAX_WAIT_TIME}s"
                    self.active_tasks[task_id]["elapsed"] = elapsed
                self.process_next_in_queue()
                return
            
            # NEW: Check GPU API for task status (every 5 seconds)
            if time.time() - last_api_check > CHECK_INTERVAL:
                last_api_check = time.time()
                try:
                    response = requests.get(
                        f"http://127.0.0.1:{port}/easy/query?code={task_id}",
                        timeout=3
                    )
                    if response.status_code == 200:
                        result = response.json()
                        data = result.get('data', {})
                        status_code = data.get('status', 0)
                        
                        # Status codes: 0=pending, 1=processing, 2=completed, 3=failed
                        if status_code == 3:  # Failed
                            error_msg = data.get('msg', 'Unknown error')
                            print(f"❌ GPU reports FAILED: {task_id}")
                            print(f"   Error: {error_msg[:200]}")
                            
                            with self.lock:
                                self.gpu_config[gpu_id]["busy"] = False
                                print(f"🟢 GPU {gpu_id} FREED (task failed)")
                                self.active_tasks[task_id]["status"] = "failed"
                                self.active_tasks[task_id]["error"] = error_msg[:500]
                                self.active_tasks[task_id]["elapsed"] = elapsed
                            
                            self.process_next_in_queue()
                            return
                        elif status_code == 2:  # Completed but file not found yet
                            print(f"   ℹ️ GPU reports completed, waiting for file...")
                            
                except Exception as e:
                    # API check failed, continue waiting
                    pass
            
            # Check if output file exists
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
                    output_dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", output_name)
                    subprocess.run(['cp', output_file, output_dest])
                    
                    # Update status
                    # Use the peak memory observed during polling
                    final_mem = f"{max_memory} MiB (Peak)" if max_memory > 0 else "Unknown"
                    with self.lock:
                        self.gpu_config[gpu_id]["busy"] = False
                        print(f"🟢 GPU {gpu_id} FREED (completed)")
                        self.active_tasks[task_id]["status"] = "completed"
                        self.active_tasks[task_id]["elapsed"] = elapsed
                        self.active_tasks[task_id]["output"] = output_name
                        self.completed_tasks.append({
                            "task_id": task_id,
                            "gpu_id": gpu_id,
                            "elapsed": elapsed,
                            "output": output_name,
                            "tts_duration": self.active_tasks[task_id].get("tts_duration", 0.0),
                            "gpu_memory_usage": final_mem,
                            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    
                    print(f"✅ '{task_id}' completed on GPU {gpu_id} ({elapsed/60:.1f} mins)")
                    
                    # Auto-Upload to YouTube/Vimeo
                    try:
                        uploader_script = "/nvme0n1-disk/nvme01/HeyGem/uploader/upload_task.py"
                        print(f"📤 Triggering auto-upload for {task_id}...")
                        subprocess.Popen(['python3', uploader_script, output_dest, '--task_id', task_id])
                    except Exception as e:
                        print(f"❌ Failed to trigger uploader: {e}")
                    
                    # Process next task in queue
                    self.process_next_in_queue()
                    break
            
            
            # Polling Logic: Check usage every 2 seconds while waiting
            # Only if GPU is marked busy (which it is)
            current_mem_str = self.get_gpu_memory(gpu_id)
            try:
                # Extract number from "1234 MiB"
                mem_val = int(current_mem_str.split()[0])
                if mem_val > max_memory:
                    max_memory = mem_val
            except:
                pass

            time.sleep(2)
    
    def add_task(self, video_path: str, audio_path: str, text: str = "", task_id: str = None, tts_duration: float = 0.0):
        """Add task to queue"""
        if task_id is None:
            task_id = f"task_{int(time.time())}"
        
        task = {
            "task_id": task_id,
            "video_path": video_path,
            "audio_path": audio_path,
            "text": text,
            "tts_duration": tts_duration,
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
        # CRITICAL FIX: Find GPU and mark it busy ATOMICALLY in one lock to prevent race conditions
        with self.lock:
            if not self.task_queue:
                return  # Queue empty
            
            # Find available GPU while holding the lock
            gpu_id = None
            for gid in [0, 1, 2]:
                if not self.gpu_config[gid]["busy"]:
                    gpu_id = gid
                    break
            
            if gpu_id is None:
                return  # All GPUs busy
            
            # Pop task and mark GPU as busy ATOMICALLY
            task = self.task_queue.pop(0)  # FIFO
            self.gpu_config[gpu_id]["busy"] = True
            print(f"🔒 LOCKED: Assigned GPU {gpu_id} to task {task['task_id']}")
        
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
                    "text": task.get("text", ""),
                    "tts_duration": task.get("tts_duration", 0.0)
                }
        else:
            # Re-queue on failure and FREE GPU
            with self.lock:
                self.task_queue.insert(0, task)
                self.gpu_config[gpu_id]["busy"] = False
    
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
                        "tts_duration": float(task.get("tts_duration", 0.0)),
                        "tts_duration": float(task.get("tts_duration", 0.0)),
                        "gpu_memory_usage": task.get("gpu_memory_usage", "N/A"),
                        "completed_at": task.get("completed_at", ""),
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
            
            # Check if in pre-processing
            if task_id in self.pre_processing_tasks:
                 return {
                     "status": "preparing",
                     "message": self.pre_processing_tasks[task_id]
                 }

            return {"status": "not_found"}

    def set_preprocessing_status(self, task_id: str, status_msg: str):
        """Update status for tasks in audio/TTS phase"""
        with self.lock:
            self.pre_processing_tasks[task_id] = status_msg
            
    def clear_preprocessing_status(self, task_id: str):
        """Remove from pre-processing (once moved to GPU queue)"""
        with self.lock:
             if task_id in self.pre_processing_tasks:
                 del self.pre_processing_tasks[task_id]


# Global scheduler instance
scheduler = SimpleGPUScheduler()


if __name__ == "__main__":
    print("🚀 Simple GPU Scheduler - 1 GPU = 1 Video")
    print("=" * 80)
    print("3 GPUs available for parallel processing")
    print("=" * 80)
