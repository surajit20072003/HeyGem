#!/usr/bin/env python3
"""
Chunked GPU Scheduler - 3 GPU Parallel Processing
Splits audio into 3 chunks, processes in parallel, then merges
"""
import requests
import json
import time
import subprocess
import os
import threading
import random
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path


class ChunkedGPUScheduler:
    def __init__(self):
        # GPU configuration
        self.gpu_config = {
            0: {"port": 8390, "busy": False},
            1: {"port": 8391, "busy": False},
            2: {"port": 8392, "busy": False}
        }
        
        # GPU data directories (host paths)
        self.gpu_data_dirs = {
            0: os.path.expanduser("~/heygem_data/gpu0/face2face"),
            1: os.path.expanduser("~/heygem_data/gpu1/face2face"),
            2: os.path.expanduser("~/heygem_data/gpu2/face2face")
        }
        
        # Task tracking
        self.active_tasks = {}  # {task_id: {status, chunks, etc}}
        self.pre_processing_tasks = {} # {task_id: "status_message"}
        self.active_tasks = {}  # {task_id: {status, chunks, etc}}
        self.pre_processing_tasks = {} # {task_id: "status_message"}
        self.task_queue = [] # LIST of tasks waiting to run
        self.lock = threading.Lock()

    def get_gpu_memory(self, gpu_id: int) -> str:
        """Get current GPU memory usage via nvidia-smi"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits', '-i', str(gpu_id)],
                capture_output=True, text=True
            )
            return f"{result.stdout.strip()} MiB"
        except Exception:
            return "0 MiB"
        
    def log(self, message: str, task_id: str = ""):
        """Thread-safe logging"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefix = f"[{task_id}] " if task_id else ""
        print(f"[{timestamp}] {prefix}{message}")
    
    def pad_audio(self, audio_path: str, min_duration: float = 4.0) -> str:
        """Pad audio with silence if shorter than min_duration"""
        try:
            duration = self.get_audio_duration(audio_path)
            if duration >= min_duration:
                return audio_path
                
            self.log(f"⚠️ Audio too short ({duration:.2f}s), padding to {min_duration}s...")
            
            output_path = audio_path.replace(".wav", "_padded.wav")
            pad_duration = min_duration - duration + 0.1 # Add slight buffer
            
            cmd = [
                '/usr/bin/ffmpeg', '-y',
                '-i', audio_path,
                '-af', f'apad=pad_dur={pad_duration}',
                '-t', str(min_duration),
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            # Replace original if successful
            os.rename(output_path, audio_path)
            return audio_path
            
        except Exception as e:
            self.log(f"❌ Padding failed: {e}")
            return audio_path

    def get_audio_duration(self, audio_file: str) -> float:
        """Get audio duration using ffprobe"""
        cmd = [
            '/usr/bin/ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    
    def split_audio(self, audio_file: str, num_chunks: int = 3) -> List[str]:
        """Split audio into equal chunks (simple time-based split)"""
        self.log(f"✂️  Splitting audio into {num_chunks} chunks...")
        
        duration = self.get_audio_duration(audio_file)
        chunk_duration = duration / num_chunks
        
        base_name = audio_file.rsplit('.', 1)[0]
        output_files = []
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            output = f"{base_name}_chunk{i+1:02d}.wav"
            
            cmd = [
                '/usr/bin/ffmpeg', '-y', '-i', audio_file,
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                output
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            self.log(f"   Chunk {i+1}/{num_chunks}: {chunk_duration:.1f}s → {os.path.basename(output)}")
            output_files.append(output)
            
        return output_files
    
    def split_video(self, video_file: str, chunk_durations: List[float]) -> List[str]:
        """Split video based on audio chunk durations (Legacy Mode - No Looping)"""
        self.log(f"✂️  Splitting video (Legacy Mode)...")
        
        base_name = video_file.rsplit('.', 1)[0]
        output_files = []
        current_start = 0.0
        
        for i, duration in enumerate(chunk_durations):
            output = f"{base_name}_chunk{i+1:02d}.mp4"
            
            cmd = [
                '/usr/bin/ffmpeg', '-y',
                '-i', video_file,
                '-ss', str(current_start),
                '-t', str(duration),
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-an',
                output
            ]
            
            # Legacy: Simple run, no validation
            subprocess.run(cmd, capture_output=True, check=True)
            output_files.append(output)
            current_start += duration
            
        return output_files
    
    def submit_to_gpu(self, gpu_id: int, video_path: str, audio_path: str, task_code: str) -> bool:
        """Submit task to specific GPU"""
        port = self.gpu_config[gpu_id]["port"]
        gpu_data_dir = self.gpu_data_dirs[gpu_id]
        
        # Create directory if not exists
        os.makedirs(gpu_data_dir, exist_ok=True)
        
        try:
            # Copy files to GPU directory
            subprocess.run(['cp', video_path, gpu_data_dir], check=True)
            subprocess.run(['cp', audio_path, gpu_data_dir], check=True)
            
            # Submit to HeyGem API
            payload = {
                "audio_url": f"/code/data/face2face/{os.path.basename(audio_path)}",
                "video_url": f"/code/data/face2face/{os.path.basename(video_path)}",
                "code": task_code,
                "chaofen": 1,
                "watermark_switch": 0,
                "pn": 1
            }
            
            response = requests.post(
                f"http://127.0.0.1:{port}/easy/submit",
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            if result.get('success'):
                with self.lock:
                    self.gpu_config[gpu_id]["busy"] = True
                self.log(f"✅ Chunk '{task_code}' → GPU {gpu_id} (Port {port})")
                return True
            else:
                self.log(f"❌ Submission failed: {result}")
                return False
                
        except Exception as e:
            self.log(f"❌ API error: {e}")
            return False
    
    def monitor_chunk(self, gpu_id: int, task_code: str) -> Tuple[str, str]:
        """Monitor a specific chunk task on a GPU (simplified - no duration tracking)"""
        # Use simple path pattern like webapp_multi_video (works with symlinks)
        output_path = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/temp/{task_code}-r.mp4")
        
        self.log(f"🔍 Monitoring GPU {gpu_id} - Task '{task_code}'")
        self.log(f"   Watching: {output_path}")
        
        start_time = time.time()
        timeout_seconds = 600 # Back to 10 minutes fixed
        max_mem = 0
        
        while True:
            # Timeout Check
            if time.time() - start_time > timeout_seconds:
                # Still log timeout but maybe don't kill aggressively? 
                # No, legacy had no kill logic inside monitor_chunk originally, 
                # but we need some exit. We'll keep the return None but with 600s.
                self.log(f"❌ Timeout waiting for chunk {task_code} (> {timeout_seconds}s)")
                return None, "0 MiB"
                
            if os.path.exists(output_path):
                # Wait for file stability
                prev_size = 0
                stable_count = 0
                
                while stable_count < 3:
                    time.sleep(2)
                    current_size = os.path.getsize(output_path)
                    
                    if current_size == prev_size and current_size > 10000:
                        stable_count += 1
                    else:
                        stable_count = 0
                        prev_size = current_size
                
                elapsed = time.time() - start_time
                
                # Mark GPU as free
                with self.lock:
                    self.gpu_config[gpu_id]["busy"] = False
                
                final_mem = f"{max_mem} MiB"
                self.log(f"✅ GPU {gpu_id} chunk '{task_code}' complete! ({elapsed:.0f}s, {current_size/1024/1024:.1f} MB, Peak: {final_mem})")
                return output_path, final_mem
            
            # Polling memory usage
            current_mem = self.get_gpu_memory(gpu_id)
            try:
                val = int(current_mem.split()[0])
                if val > max_mem: max_mem = val
            except:
                pass

            time.sleep(2)
    
    def merge_videos(self, video_files: List[str], output_file: str) -> bool:
        """Merge video chunks using GPU-accelerated FFmpeg"""
        self.log(f"🎬 Merging {len(video_files)} video chunks...")
        
        # Create temporary file list
        list_file = '/tmp/heygem_chunked_video_list.txt'
        with open(list_file, 'w') as f:
            for video in video_files:
                f.write(f"file '{video}'\n")
        
        # Step 1: Fast concatenation without re-encoding
        temp_concat = output_file.replace('.mp4', '_temp_concat.mp4')
        
        cmd_concat = [
            '/usr/bin/ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            temp_concat
        ]
        
        self.log("   Step 1/2: Concatenating chunks...")
        result = subprocess.run(cmd_concat, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.log(f"❌ Concat failed: {result.stderr[:200]}")
            os.remove(list_file)
            return False
        
        # Step 2: GPU re-encode for optimal quality
        self.log("   Step 2/2: GPU encoding final video...")
        cmd_encode = [
            '/usr/bin/ffmpeg', '-y',
            '-hwaccel', 'cuda',
            '-i', temp_concat,
            '-c:v', 'h264_nvenc',
            '-preset', 'fast',
            '-b:v', '3M',
            '-c:a', 'copy',
            output_file
        ]
        
        result = subprocess.run(cmd_encode, capture_output=True, text=True)
        
        # Cleanup
        if result.returncode == 0:
            self.log(f"✅ GPU-accelerated merge complete!")
            if os.path.exists(temp_concat):
                os.remove(temp_concat)
        else:
            # Fallback: use concatenated version
            self.log("⚠️  GPU encoding failed, using concatenated version")
            if os.path.exists(temp_concat):
                os.rename(temp_concat, output_file)
        
        os.remove(list_file)
        return os.path.exists(output_file)
    
    def process_chunked_task(self, video_path: str, audio_path: str, task_id: str):
        """Main chunked processing workflow (runs in background thread)"""
        try:
            self.log(f"🚀 Starting chunked processing", task_id)
            
            with self.lock:
                self.active_tasks[task_id] = {
                    "status": "splitting",
                    "chunks": [],
                    "start_time": time.time(),
                    "tts_duration": self.active_tasks[task_id].get("tts_duration", 0.0)
                }
            
            # Step 1: Split audio into 3 chunks
            audio_chunks = self.split_audio(audio_path, num_chunks=3)
            
            # Step 2: Use FULL video for all chunks (like webapp_multi_video)
            # HeyGen API will auto-trim video to match audio duration
            # This fixes CUDA stream capturing errors on GPU 1 & 2
            video_chunks = [video_path, video_path, video_path]
            self.log(f"📹 Using full video for all chunks (HeyGen API auto-trims to audio)", task_id)
            
            # Step 3: Submit pairs to GPUs
            self.log(f"🎬 Submitting 3 chunks to GPUs", task_id)
            
            # Get available GPUs dynamically
            with self.lock:
                available_gpus = [gid for gid in [0, 1, 2] if not self.gpu_config[gid]["busy"]]
                gpu_status = {gid: "FREE" if not self.gpu_config[gid]["busy"] else "BUSY" 
                             for gid in [0, 1, 2]}
            
            self.log(f"📊 GPU Status: GPU0={gpu_status[0]}, GPU1={gpu_status[1]}, GPU2={gpu_status[2]}", task_id)
            self.log(f"✅ Available GPUs: {available_gpus}", task_id)
            
            # Check if we have enough GPUs
            if len(available_gpus) < 3:
                self.log(f"⚠️  Only {len(available_gpus)} GPUs available, need 3. Waiting...", task_id)
                # Could implement waiting logic here, but for now proceed with available
            
            chunk_tasks = []
            chunk_outputs = []
            
            # Dynamic GPU assignment based on availability
            for i in range(3):
                audio_chunk = audio_chunks[i]
                video_chunk = video_chunks[i] if i < len(video_chunks) else video_path # Fallback
                
                # Assign to next available GPU (dynamic)
                if i < len(available_gpus):
                    gpu_id = available_gpus[i]
                else:
                    # Fallback: use GPU 0 if not enough available
                    gpu_id = 0
                    self.log(f"⚠️  Not enough free GPUs, falling back to GPU 0 for chunk {i+1}", task_id)
                
                self.log(f"🎯 Assigning Chunk {i+1} → GPU {gpu_id}", task_id)
                
                chunk_code = f"{task_id}_chunk{i+1:02d}"
                
                # Submit to GPU
                success = self.submit_to_gpu(gpu_id, video_chunk, audio_chunk, chunk_code)
                
                if not success:
                    self.log(f"❌ Failed to submit chunk {i+1}", task_id)
                    with self.lock:
                        self.active_tasks[task_id]["status"] = "failed"
                        self.active_tasks[task_id]["error"] = f"Chunk {i+1} submission failed"
                    return
                
                # Start monitoring in background
                def monitor_wrapper(gpu, code, index):
                    # Simplified - no duration tracking needed
                    output, mem = self.monitor_chunk(gpu, code)
                    
                    if output is None:
                         with self.lock:
                             self.active_tasks[task_id]["status"] = "failed"
                             self.active_tasks[task_id]["error"] = f"Timeout/Error on GPU {gpu}"
                         return
                         
                    with self.lock:
                        chunk_outputs.append((index, output, mem))
                
                thread = threading.Thread(
                    target=monitor_wrapper,
                    args=(gpu_id, chunk_code, i),  # Removed chunk_durations[i]
                    daemon=True
                )
                thread.start()
                chunk_tasks.append(thread)
                
                time.sleep(0.5)  # Small delay
            
            # Update status
            with self.lock:
                self.active_tasks[task_id]["status"] = "processing"
                self.active_tasks[task_id]["chunks"] = [
                    {"gpu_id": i, "status": "processing"} for i in range(3)
                ]
            
            # Step 3: Wait for all chunks to complete
            self.log(f"⏳ Waiting for all 3 chunks to complete", task_id)
            for thread in chunk_tasks:
                thread.join()
                
            # Check if any chunk failed (Timeout/Error)
            with self.lock:
                if self.active_tasks[task_id]["status"] == "failed":
                    self.log(f"❌ Task aborted: {self.active_tasks[task_id].get('error')}", task_id)
                    self.process_next_task()
                    return
            
            # Sort videos by chunk index
            chunk_outputs.sort(key=lambda x: x[0])
            sorted_videos = [v[1] for v in chunk_outputs]
            
            self.log(f"📊 All chunks complete. Starting merge...", task_id)
            
            # Update status
            with self.lock:
                self.active_tasks[task_id]["status"] = "merging"
            
            # Step 4: Merge videos
            base_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(base_dir, "outputs", f"output_{task_id}.mp4")
            merge_success = self.merge_videos(sorted_videos, output_file)
            
            if merge_success:
                elapsed = time.time() - self.active_tasks[task_id]["start_time"]
                
                with self.lock:
                    self.active_tasks[task_id]["status"] = "completed"
                    self.active_tasks[task_id]["output"] = output_file
                    self.active_tasks[task_id]["elapsed"] = elapsed
                    self.active_tasks[task_id]["tts_duration"] = self.active_tasks[task_id].get("tts_duration", 0.0)
                    # Aggregate memory usage
                    total_mem = " | ".join([f"GPU{v[0]}:{v[2]}" for v in chunk_outputs])
                    self.active_tasks[task_id]["gpu_memory_usage"] = total_mem
                    self.active_tasks[task_id]["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                self.log(f"✅ Task completed! ({elapsed/60:.1f} mins)", task_id)

                # Auto-Upload to YouTube/Vimeo
                try:
                    uploader_script = "/nvme0n1-disk/nvme01/HeyGem/uploader/upload_task.py"
                    self.log(f"📤 Triggering auto-upload...", task_id)
                    subprocess.Popen(['python3', uploader_script, output_file, '--task_id', task_id])
                except Exception as e:
                    self.log(f"❌ Failed to trigger uploader: {e}", task_id)
                
                # Process next in queue
                self.process_next_task()
                    
                # Process next in queue
                self.process_next_task()
            else:
                with self.lock:
                    self.active_tasks[task_id]["status"] = "failed"
                    self.active_tasks[task_id]["error"] = "Video merge failed"
                
                self.log(f"❌ Task failed: merge error", task_id)
                self.process_next_task()
                
        except Exception as e:
            self.log(f"❌ Task failed: {e}", task_id)
            with self.lock:
                self.active_tasks[task_id]["status"] = "failed"
                self.active_tasks[task_id]["error"] = str(e)
            
            # Ensure queue continues even on failure
            self.process_next_task()
    
    def process_next_task(self):
        """Check queue and start next task if system is free"""
        with self.lock:
            # Check if any task is currently running
            running_tasks = [t for t in self.active_tasks.values() 
                           if t["status"] in ["splitting", "processing", "merging", "starting"]]
            
            if len(running_tasks) > 0:
                return # Busy
                
            if not self.task_queue:
                return # Empty queue
                
            # Pop next task
            next_task = self.task_queue.pop(0)
            
            # Mark as starting IMMEDIATELY to block other threads
            if next_task["task_id"] in self.active_tasks:
                 self.active_tasks[next_task["task_id"]]["status"] = "starting"

        # Start it (outside lock to avoid deadlock during thread creation logging)
        self.log(f"🚦 Starting next queued task: {next_task['task_id']}")
        
        thread = threading.Thread(
            target=self.process_chunked_task,
            args=(next_task["video_path"], next_task["audio_path"], next_task["task_id"]),
            daemon=True
        )
        thread.start()

    def add_task(self, video_path: str, audio_path: str, text: str = "", task_id: str = None, tts_duration: float = 0.0):
        if task_id is None:
            task_id = f"chunked_{int(time.time())}"
        
        # Store initial details including tts_duration
        with self.lock:
            self.active_tasks[task_id] = {
                 "status": "queued",
                 "tts_duration": tts_duration
            }
            # Add to Queue
            self.task_queue.append({
                "task_id": task_id,
                "video_path": video_path,
                "audio_path": audio_path
            })
        
        self.log(f"📝 New chunked task queued: {task_id}")
        
        # Try to process
        self.process_next_task()
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict:
        """Get status of chunked task"""
        with self.lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                
                response = {
                    "status": task["status"],
                    "chunks": task.get("chunks", [])
                }
                
                if task["status"] == "completed":
                    response["elapsed_seconds"] = int(task.get("elapsed", 0))
                    response["tts_duration"] = float(task.get("tts_duration", 0.0))
                    response["elapsed_seconds"] = int(task.get("elapsed", 0))
                    response["tts_duration"] = float(task.get("tts_duration", 0.0))
                    response["gpu_memory_usage"] = task.get("gpu_memory_usage", "N/A")
                    response["completed_at"] = task.get("completed_at", "")
                    response["output"] = task.get("output", "")
                elif task["status"] == "failed":
                    response["error"] = task.get("error", "Unknown error")
                elif task["status"] in ["processing", "splitting", "merging"]:
                    elapsed = time.time() - task["start_time"]
                    response["elapsed_seconds"] = int(elapsed)
                
                return response
                return response
            else:
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
    
    def get_gpu_status(self) -> Dict:
        """Get current GPU status"""
        with self.lock:
            return {
                "gpu0": {"status": "busy" if self.gpu_config[0]["busy"] else "free", "memory": self.get_gpu_memory(0)},
                "gpu1": {"status": "busy" if self.gpu_config[1]["busy"] else "free", "memory": self.get_gpu_memory(1)},
                "gpu2": {"status": "busy" if self.gpu_config[2]["busy"] else "free", "memory": self.get_gpu_memory(2)},
                "active_tasks": len([t for t in self.active_tasks.values() 
                                   if t["status"] in ["splitting", "processing", "merging"]])
            }


# Global scheduler instance
scheduler = ChunkedGPUScheduler()


if __name__ == "__main__":
    print("🚀 Chunked GPU Scheduler - 3 GPU Parallel Processing")
    print("=" * 80)
    print("Splits audio into 3 chunks, processes in parallel, then merges")
    print("=" * 80)
