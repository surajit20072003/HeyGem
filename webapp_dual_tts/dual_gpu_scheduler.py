#!/usr/bin/env python3
"""
Triple GPU Scheduler with Dedicated TTS Containers
- GPU 0 (Port 8390) → TTS 0 (Port 18182)
- GPU 1 (Port 8391) → TTS 1 (Port 18183)
- GPU 2 (Port 8392) → TTS 2 (Port 18184)
- Proper queue management
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


class DualGPUScheduler:
    def __init__(self):
        # 3 GPUs with dedicated TTS services
        self.gpu_config = {
            0: {
                "port": 8390,
                "tts_port": 18182,  # Dedicated TTS for GPU 0 (heygem-tts-dual-0)
                "busy": False,
                "current_task": None
            },
            1: {
                "port": 8391,
                "tts_port": 18183,  # Dedicated TTS for GPU 1 (heygem-tts-dual-1)
                "busy": False,
                "current_task": None
            },
            2: {
                "port": 8392,
                "tts_port": 18184,  # Dedicated TTS for GPU 2 (heygem-tts-dual-2)
                "busy": False,
                "current_task": None
            }
        }
        
        # Task management
        self.task_queue = Queue()
        self.active_tasks = {}  # task_id -> {status, gpu_id, progress, ...}
        self.preprocessing_tasks = {}  # Tasks in audio extraction/TTS phase
        
        # Threading
        self.lock = threading.Lock()
        
        print("🚀 Triple GPU Scheduler Initialized")
        print(f"   GPU 0: Video Port {self.gpu_config[0]['port']}, TTS Port {self.gpu_config[0]['tts_port']} (heygem-tts-dual-0)")
        print(f"   GPU 1: Video Port {self.gpu_config[1]['port']}, TTS Port {self.gpu_config[1]['tts_port']} (heygem-tts-dual-1)")
        print(f"   GPU 2: Video Port {self.gpu_config[2]['port']}, TTS Port {self.gpu_config[2]['tts_port']} (heygem-tts-dual-2)")

    def get_gpu_memory(self, gpu_id: int) -> str:
        """Get current GPU memory usage via nvidia-smi"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits', f'--id={gpu_id}'],
                capture_output=True, text=True, timeout=5
            )
            return f"{result.stdout.strip()} MiB"
        except Exception:
            return "N/A"
    
    def get_gpu_utilization(self, gpu_id: int) -> int:
        """Get current GPU utilization percentage"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits', f'--id={gpu_id}'],
                capture_output=True, text=True, timeout=5
            )
            return int(result.stdout.strip())
        except Exception:
            return 0

    def find_available_gpu(self) -> Optional[int]:
        """
        Find first free GPU (0, 1, or 2)
        Returns: GPU ID or None if all busy
        """
        with self.lock:
            for gpu_id in [0, 1, 2]:  # All 3 GPUs
                if not self.gpu_config[gpu_id]["busy"]:
                    return gpu_id
        return None

    def reserve_gpu_for_task(self, task_id: str) -> Optional[int]:
        """
        Atomically reserve a GPU for the entire task lifecycle.
        This ensures TTS and video generation happen on the SAME GPU.
        Returns: GPU ID if available, None if all busy (task should queue)
        """
        with self.lock:
            for gpu_id in [0, 1, 2]:  # Check all 3 GPUs
                if not self.gpu_config[gpu_id]["busy"]:
                    # Reserve immediately - atomic operation
                    self.gpu_config[gpu_id]["busy"] = True
                    self.gpu_config[gpu_id]["current_task"] = task_id
                    
                    # Track reservation
                    self.active_tasks[task_id] = {
                        "status": "reserved",
                        "gpu_id": gpu_id,
                        "progress": 0,
                        "reserved_time": datetime.now()
                    }
                    
                    print(f"🔒 [GPU {gpu_id}] Reserved for task {task_id}")
                    return gpu_id
        
        # All GPUs busy
        print(f"⏸️  [Task {task_id}] All GPUs busy - will queue")
        return None

    def release_gpu(self, gpu_id: int, task_id: str):
        """
        Release GPU and trigger next task in queue.
        Called when task completes, fails, or times out.
        """
        with self.lock:
            if self.gpu_config[gpu_id]["current_task"] == task_id:
                self.gpu_config[gpu_id]["busy"] = False
                self.gpu_config[gpu_id]["current_task"] = None
                print(f"🔓 [GPU {gpu_id}] Released from task {task_id}")
            else:
                print(f"⚠️  [GPU {gpu_id}] Release called but current task is {self.gpu_config[gpu_id]['current_task']}, not {task_id}")
        
        # Process next in queue with TTS callback
        queued_processor = getattr(self, 'queued_task_processor', None)
        self.process_next_in_queue(queued_task_processor=queued_processor)

    def get_gpu_status(self) -> Dict:
        """Get status of both GPUs"""
        with self.lock:
            return {
                gpu_id: {
                    "busy": config["busy"],
                    "current_task": config["current_task"],
                    "memory_used": self.get_gpu_memory(gpu_id),
                    "gpu_utilization": self.get_gpu_utilization(gpu_id),
                    "video_port": config["port"],
                    "tts_port": config["tts_port"]
                }
                for gpu_id, config in self.gpu_config.items()
            }

    def submit_to_gpu(self, video_path: str, audio_path: str, task_id: str, gpu_id: int) -> bool:
        """
        Submit video generation task to specific GPU.
        Note: GPU should already be reserved via reserve_gpu_for_task()
        """
        import shutil
        
        port = self.gpu_config[gpu_id]["port"]
        
        print(f"\n📤 [GPU {gpu_id}] Submitting task {task_id}")
        print(f"   Original Video: {video_path}")
        print(f"   Original Audio: {audio_path}")
        print(f"   Port: {port}")
        
        # Define host shared directory for this GPU
        # /home/administrator/heygem_data/gpu0 or gpu1
        host_shared_dir = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}")
        os.makedirs(host_shared_dir, exist_ok=True)
        
        # Define filenames
        video_filename = os.path.basename(video_path)
        audio_filename = os.path.basename(audio_path)
        
        # Copy files to shared directory
        try:
            # Copy video
            dest_video_path = os.path.join(host_shared_dir, video_filename)
            print(f"   Copying video to: {dest_video_path}")
            shutil.copy2(video_path, dest_video_path)
            
            # Copy audio
            dest_audio_path = os.path.join(host_shared_dir, audio_filename)
            print(f"   Copying audio to: {dest_audio_path}")
            shutil.copy2(audio_path, dest_audio_path)
            
        except Exception as e:
            print(f"❌ [GPU {gpu_id}] Error copying files: {e}")
            return False

        # Construct container-internal paths
        # Container sees /home/administrator/heygem_data/gpuX as /code/data
        container_video_path = f"/code/data/{video_filename}"
        container_audio_path = f"/code/data/{audio_filename}"
        
        print(f"   Container Video: {container_video_path}")
        print(f"   Container Audio: {container_audio_path}")
        
        payload = {
            "audio_url": container_audio_path,
            "video_url": container_video_path,
            "code": task_id,
            "chaofen": 0,
            "watermark_switch": 0,
            "pn": 1
        }
        
        try:
            response = requests.post(
                f"http://localhost:{port}/easy/submit",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ [GPU {gpu_id}] Task submitted successfully")
                
                # Update task status (GPU already marked as busy)
                with self.lock:
                    if task_id in self.active_tasks:
                        self.active_tasks[task_id]["status"] = "processing"
                        self.active_tasks[task_id]["start_time"] = datetime.now()
                        self.active_tasks[task_id]["video_start_time"] = time.time()  # Track video processing start
                        self.active_tasks[task_id]["video_path"] = video_path
                        self.active_tasks[task_id]["audio_path"] = audio_path
                
                # Start monitoring in background
                monitor_thread = threading.Thread(
                    target=self.monitor_task,
                    args=(task_id, gpu_id, video_path, audio_path),
                    daemon=True
                )
                monitor_thread.start()
                return True
            else:
                print(f"❌ [GPU {gpu_id}] Submission failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ [GPU {gpu_id}] Error submitting: {e}")
            return False


    def monitor_task(self, task_id: str, gpu_id: int, video_path: str, audio_path: str):
        """Monitor task until completion with timeout and failure detection"""
        port = self.gpu_config[gpu_id]["port"]
        max_wait = 1800  # 30 minutes timeout
        check_interval = 5
        elapsed = 0
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        print(f"👁️ [GPU {gpu_id}] Monitoring task {task_id}")
        
        while elapsed < max_wait:
            try:
                response = requests.get(
                    f"http://localhost:{port}/easy/query?code={task_id}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    consecutive_errors = 0  # Reset error counter
                    result = response.json()
                    
                    # DEBUG: Print full result structure once every 10 seconds or on change
                    if elapsed % 10 == 0:
                        print(f"   [DEBUG] GPU {gpu_id} Response: {str(result)[:200]}...")
                    
                    data = result.get('data', {})
                    if data is None: data = {}
                    
                    status = data.get('status', 'unknown')
                    progress = data.get('progress', 0)
                    
                    # If status is unknown, check top-level keys
                    if status == 'unknown':
                        if result.get('code') == 0 and result.get('msg') == 'success':
                            # Sometimes success without data might mean queued or processing
                            pass
                            
                    # Update task status
                    with self.lock:
                        if task_id in self.active_tasks:
                            self.active_tasks[task_id]["progress"] = progress
                            self.active_tasks[task_id]["raw_status"] = status
                    
                    print(f"   [{elapsed}s] GPU {gpu_id} - Status: {status}, Progress: {progress}%")
                    
                    # Check if completed
                    # Status 2 = Success/Done, Status 3 = Failed? (based on observation)
                    is_completed = (
                        status in ['completed', 'finished', 'done', 2, '2'] or 
                        'result' in result or 
                        progress == 100
                    )
                    
                    if is_completed:
                        print(f"✅ [GPU {gpu_id}] Task {task_id} completed!")
                        
                        # Handle Result File
                        # Handle Result File
                        # Result from GPU: "/code/data/temp/task_.../result.avi" or "/task_...mp4"
                        container_result_path = result.get('data', {}).get('result', '')
                        
                        # Strip /code/data/ prefix
                        if container_result_path.startswith('/code/data/'):
                            rel_path = container_result_path[len('/code/data/'):]
                        elif container_result_path.startswith('/'):
                            rel_path = container_result_path[1:]
                        else:
                            rel_path = container_result_path
                            
                        # Source path in shared volume
                        host_shared_dir = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}")
                        source_path = os.path.join(host_shared_dir, rel_path)
                        
                        print(f"   [DEBUG] Container Path: {container_result_path}")
                        print(f"   [DEBUG] Host Source Path: {source_path}")
                        
                        # Destination path in webapp outputs
                        # Use mp4 extension for output
                        output_filename = f"final_{task_id}.mp4"
                        dest_path = os.path.join(os.getcwd(), 'outputs', output_filename)
                        
                        final_url = ""
                        
                        # Try to find the file
                        found = False
                        if os.path.exists(source_path):
                            found = True
                        else:
                            # STRICT: Only look for the file named with task_id and -r.mp4 extension
                            # This ensures we always get the file with merged audio.
                            # Format: {task_id}-r.mp4 (task_id usually includes "task_" prefix already)
                            
                            if task_id.startswith("task_"):
                                expected_filename = f"{task_id}-r.mp4"
                            else:
                                expected_filename = f"task_{task_id}-r.mp4"
                                
                            print(f"   [INFO] Looking for specific output file: {expected_filename}")

                            candidates = [
                                os.path.join(host_shared_dir, "temp", expected_filename),
                                os.path.join(host_shared_dir, expected_filename)
                            ]
                            
                            for p in candidates:
                                if os.path.exists(p):
                                    source_path = p
                                    found = True
                                    print(f"   [DEBUG] Found strict match: {source_path}")
                                    break
                        
                        if found:
                            import shutil
                            
                            # Wait for file stability (matching webapp implementation)
                            print(f"   ⏳ Waiting for file to be completely written...")
                            prev_size = 0
                            stable_count = 0
                            
                            while stable_count < 3:  # Need 3 consecutive stable checks
                                time.sleep(2)
                                current_size = os.path.getsize(source_path)
                                
                                if current_size == prev_size and current_size > 10000:
                                    stable_count += 1
                                else:
                                    stable_count = 0
                                    prev_size = current_size
                            
                            print(f"   📁 File stable: {current_size/1024/1024:.1f} MB")
                            
                            # Validate file size
                            if current_size < 100000:  # Less than 100KB is suspicious for video
                                print(f"   ⚠️ Output file too small ({current_size} bytes), may be corrupted")
                                with self.lock:
                                    self.active_tasks[task_id]["status"] = "failed"
                                    self.active_tasks[task_id]["error"] = f"Output file too small: {current_size} bytes"
                                self.release_gpu(gpu_id, task_id)
                                return
                            
                            # Copy to output directory
                            shutil.copy2(source_path, dest_path)
                            print(f"   💾 Saved output to: {dest_path}")
                            final_url = f"/outputs/{output_filename}"
                        else:
                            print(f"   ⚠️ Result file not found at: {source_path}")
                            # Mark as failed instead of completed
                            with self.lock:
                                self.active_tasks[task_id]["status"] = "failed"
                                self.active_tasks[task_id]["error"] = "Result file not found"
                            self.release_gpu(gpu_id, task_id)
                            return
                        
                        # Update Result Payload - add defensive check
                        if result.get('data') is not None:
                            result['data']['result_url'] = final_url
                        
                        # Calculate video generation time
                        video_time = None
                        with self.lock:
                            if task_id in self.active_tasks and "video_start_time" in self.active_tasks[task_id]:
                                video_time = time.time() - self.active_tasks[task_id]["video_start_time"]
                                print(f"   ⏱️  Video generation time: {video_time:.2f}s")
                        
                        with self.lock:
                            self.active_tasks[task_id]["status"] = "completed"
                            self.active_tasks[task_id]["result"] = result
                            self.active_tasks[task_id]["completed_time"] = datetime.now()
                            if video_time is not None:
                                self.active_tasks[task_id]["video_time"] = video_time
                        
                        # Release GPU and process next task
                        self.release_gpu(gpu_id, task_id)
                        return
                    
                    # Check for explicit failure
                    if status in ['failed', 'error']:
                        print(f"❌ [GPU {gpu_id}] Task {task_id} failed!")
                        
                        with self.lock:
                            self.active_tasks[task_id]["status"] = "failed"
                            self.active_tasks[task_id]["error"] = f"Task failed with status: {status}"
                        
                        self.process_next_in_queue()
                        return
                
                else:
                    consecutive_errors += 1
                    print(f"⚠️ [GPU {gpu_id}] Query error ({consecutive_errors}/{max_consecutive_errors}): {response.status_code}")
                
            except Exception as e:
                consecutive_errors += 1
                print(f"⚠️ [GPU {gpu_id}] Monitor error ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            # Check if too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                print(f"❌ [GPU {gpu_id}] Too many errors, marking task as failed")
                
                with self.lock:
                    self.active_tasks[task_id]["status"] = "failed"
                    self.active_tasks[task_id]["error"] = "Too many consecutive monitoring errors"
                
                # Release GPU and process next task
                self.release_gpu(gpu_id, task_id)
                return
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        # Timeout occurred
        print(f"⏰ [GPU {gpu_id}] Task {task_id} timed out after {max_wait}s")
        
        with self.lock:
            self.active_tasks[task_id]["status"] = "timeout"
            self.active_tasks[task_id]["error"] = f"Timeout after {max_wait} seconds"
        
        # Release GPU and process next task
        self.release_gpu(gpu_id, task_id)

    def add_task(self, video_path: str, audio_path: str, text: str = "", task_id: str = None, tts_duration: float = 0.0) -> str:
        """Add task to queue"""
        if task_id is None:
            task_id = f"task_{int(time.time())}"
        
        print(f"\n➕ Adding task {task_id} to queue")
        print(f"   Video: {video_path}")
        print(f"   Audio: {audio_path}")
        print(f"   Text: {text[:50]}..." if len(text) > 50 else f"   Text: {text}")
        
        # Add to queue
        self.task_queue.put({
            "task_id": task_id,
            "video_path": video_path,
            "audio_path": audio_path,
            "text": text,
            "tts_duration": tts_duration,
            "queued_time": datetime.now()
        })
        
        # Initialize task status
        with self.lock:
            self.active_tasks[task_id] = {
                "status": "queued",
                "progress": 0,
                "queued_time": datetime.now(),
                "text": text
            }
        
        # Try to process immediately
        self.process_next_in_queue()
        
        return task_id

    def add_to_queue_only(self, task_id: str, video_path: str, audio_path: str, text: str):
        """
        Add task to queue without trying to process.
        Used when all GPUs are busy during initial request.
        """
        print(f"\n📥 Adding task {task_id} to queue (all GPUs busy)")
        print(f"   Video: {video_path}")
        print(f"   Audio: {audio_path}")
        
        # Add to queue
        self.task_queue.put({
            "task_id": task_id,
            "video_path": video_path,
            "audio_path": audio_path,
            "text": text,
            "queued_time": datetime.now()
        })
        
        # Mark as queued
        with self.lock:
            self.active_tasks[task_id] = {
                "status": "queued",
                "progress": 0,
                "queued_time": datetime.now(),
                "text": text
            }

    def process_next_in_queue(self, queued_task_processor=None):
        """
        Process next task if GPU available.
        If queued_task_processor callback is provided, it will be called to handle
        TTS generation for queued tasks.
        """
        if self.task_queue.empty():
            print("📭 Queue is empty")
            return
        
        # Check for available GPU and reserve it atomically
        gpu_id = None
        with self.lock:
            for gid in [0, 1, 2]:  # Check all 3 GPUs
                if not self.gpu_config[gid]["busy"]:
                    gpu_id = gid
                    break
        
        if gpu_id is None:
            print("⏸️ No GPUs available, tasks remain in queue")
            return
        
        # Get next task
        task_data = self.task_queue.get()
        task_id = task_data["task_id"]
        
        print(f"\n🎬 Processing queued task: {task_id}")
        print(f"   Will assign to GPU {gpu_id}")
        print(f"   Queue size remaining: {self.task_queue.qsize()}")
        
        # Reserve the GPU for this task
        with self.lock:
            self.gpu_config[gpu_id]["busy"] = True
            self.gpu_config[gpu_id]["current_task"] = task_id
            
            # Update task status
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "reserved"
                self.active_tasks[task_id]["gpu_id"] = gpu_id
        
        print(f"🔒 [GPU {gpu_id}] Reserved for queued task {task_id}")
        
        # If callback provided, use it to handle TTS generation
        if queued_task_processor is not None:
            print(f"   📝 Task has text: {task_data.get('text', 'N/A')[:50]}...")
            queued_task_processor(task_data, gpu_id)
            return
        
        # Otherwise, submit directly (audio already generated)
        success = self.submit_to_gpu(
            task_data["video_path"],
            task_data["audio_path"],
            task_id,
            gpu_id
        )
        
        if not success:
            # Submission failed, release GPU and re-queue
            print(f"⚠️ Submission failed, releasing GPU and re-queuing task {task_id}")
            self.release_gpu(gpu_id, task_id)
            self.task_queue.put(task_data)
            
            with self.lock:
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = "queued"
                    self.active_tasks[task_id]["error"] = "Submission failed, re-queued"

    def get_task_status(self, task_id: str) -> Dict:
        """Get status of specific task"""
        with self.lock:
            if task_id in self.preprocessing_tasks:
                return {
                    "status": "preprocessing",
                    "message": self.preprocessing_tasks[task_id],
                    "progress": 0
                }
            
            if task_id not in self.active_tasks:
                return {
                    "status": "not_found",
                    "error": f"Task {task_id} not found"
                }
            
            task = self.active_tasks[task_id]
            
            # Calculate total processing time
            total_time = None
            if task.get("completed_time") and task.get("start_time"):
                total_time = (task["completed_time"] - task["start_time"]).total_seconds()
            
            # Generate URL for generated audio if it exists
            generated_audio_url = None
            if task.get("generated_audio"):
                audio_filename = os.path.basename(task["generated_audio"])
                # Check if file exists in temp folder
                if os.path.exists(task["generated_audio"]):
                    generated_audio_url = f"/outputs/{audio_filename}"  # Serve from temp via outputs
            
            return {
                "status": task.get("status", "unknown"),
                "progress": task.get("progress", 0),
                "gpu_id": task.get("gpu_id"),
                "start_time": task.get("start_time").isoformat() if task.get("start_time") else None,
                "completed_time": task.get("completed_time").isoformat() if task.get("completed_time") else None,
                "error": task.get("error"),
                "result": task.get("result"),
                "queue_position": self._get_queue_position(task_id),
                "input_text": task.get("input_text"),  # Original text input
                "reference_audio": task.get("reference_audio"),  # Reference audio path
                "generated_audio_url": generated_audio_url,  # Generated TTS audio URL
                "timing": {
                    "tts_time": task.get("tts_time"),  # Voice generation time
                    "video_time": task.get("video_time"),  # Video processing time
                    "total_time": total_time  # Total time from start to completion
                }
            }

    def _get_queue_position(self, task_id: str) -> Optional[int]:
        """Get position in queue (1-indexed)"""
        queue_list = list(self.task_queue.queue)
        for idx, task_data in enumerate(queue_list):
            if task_data["task_id"] == task_id:
                return idx + 1
        return None

    def set_preprocessing_status(self, task_id: str, status_msg: str):
        """Update status for tasks in audio/TTS phase"""
        with self.lock:
            self.preprocessing_tasks[task_id] = status_msg

    def clear_preprocessing_status(self, task_id: str):
        """Remove from pre-processing (once moved to GPU queue)"""
        with self.lock:
            if task_id in self.preprocessing_tasks:
                del self.preprocessing_tasks[task_id]


# Global scheduler instance
scheduler = DualGPUScheduler()


if __name__ == "__main__":
    print("🚀 Triple GPU Scheduler with Dedicated TTS Services")
    print("=" * 80)
    print("GPU 0 (Port 8390) → TTS (Port 18182) [heygem-tts-dual-0]")
    print("GPU 1 (Port 8391) → TTS (Port 18183) [heygem-tts-dual-1]")
    print("GPU 2 (Port 8392) → TTS (Port 18184) [heygem-tts-dual-2]")
    print("=" * 80)
