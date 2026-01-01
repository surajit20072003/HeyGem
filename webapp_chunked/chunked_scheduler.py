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
        self.lock = threading.Lock()
        
    def log(self, message: str, task_id: str = ""):
        """Thread-safe logging"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefix = f"[{task_id}] " if task_id else ""
        print(f"[{timestamp}] {prefix}{message}")
    
    def get_audio_duration(self, audio_file: str) -> float:
        """Get audio duration using ffprobe"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    
    def split_audio(self, audio_file: str, num_chunks: int = 3) -> List[str]:
        """Split audio into equal chunks"""
        self.log(f"✂️  Splitting audio into {num_chunks} chunks...")
        
        duration = self.get_audio_duration(audio_file)
        chunk_duration = duration / num_chunks
        
        base_name = audio_file.rsplit('.', 1)[0]
        output_files = []
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            output = f"{base_name}_chunk{i+1:02d}.wav"
            
            cmd = [
                'ffmpeg', '-y', '-i', audio_file,
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                '-c', 'copy',
                output
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            output_files.append(output)
            self.log(f"   Chunk {i+1}/{num_chunks}: {chunk_duration:.1f}s → {os.path.basename(output)}")
        
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
    
    def monitor_chunk(self, gpu_id: int, task_code: str) -> str:
        """Monitor chunk task until completion, returns output file path"""
        # Output path: ~/heygem_data/gpu{id}/temp/{task_code}-r.mp4
        output_path = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/temp/{task_code}-r.mp4")
        
        self.log(f"🔍 Monitoring GPU {gpu_id} - Task '{task_code}'")
        self.log(f"   Watching: {output_path}")
        
        start_time = time.time()
        
        while True:
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
                
                self.log(f"✅ GPU {gpu_id} chunk '{task_code}' complete! ({elapsed:.0f}s, {current_size/1024/1024:.1f} MB)")
                return output_path
            
            time.sleep(5)
    
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
            'ffmpeg', '-y',
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
            'ffmpeg', '-y',
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
                    "start_time": time.time()
                }
            
            # Step 1: Split audio into 3 chunks
            audio_chunks = self.split_audio(audio_path, num_chunks=3)
            
            # Step 2: Submit all 3 chunks to GPUs
            self.log(f"🎬 Submitting 3 chunks to GPUs", task_id)
            
            chunk_tasks = []
            chunk_outputs = []
            
            for i, audio_chunk in enumerate(audio_chunks):
                gpu_id = i  # GPU 0, 1, 2 for chunks 1, 2, 3
                chunk_code = f"{task_id}_chunk{i+1:02d}"
                
                # Submit to GPU
                success = self.submit_to_gpu(gpu_id, video_path, audio_chunk, chunk_code)
                
                if not success:
                    self.log(f"❌ Failed to submit chunk {i+1}", task_id)
                    with self.lock:
                        self.active_tasks[task_id]["status"] = "failed"
                        self.active_tasks[task_id]["error"] = f"Chunk {i+1} submission failed"
                    return
                
                # Start monitoring in background
                def monitor_wrapper(gpu, code, index):
                    output = self.monitor_chunk(gpu, code)
                    with self.lock:
                        chunk_outputs.append((index, output))
                
                thread = threading.Thread(
                    target=monitor_wrapper,
                    args=(gpu_id, chunk_code, i),
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
            
            # Sort videos by chunk index
            chunk_outputs.sort(key=lambda x: x[0])
            sorted_videos = [v[1] for v in chunk_outputs]
            
            self.log(f"📊 All chunks complete. Starting merge...", task_id)
            
            # Update status
            with self.lock:
                self.active_tasks[task_id]["status"] = "merging"
            
            # Step 4: Merge videos
            output_file = f"/nvme0n1-disk/HeyGem/webapp_chunked/outputs/output_{task_id}.mp4"
            merge_success = self.merge_videos(sorted_videos, output_file)
            
            if merge_success:
                elapsed = time.time() - self.active_tasks[task_id]["start_time"]
                
                with self.lock:
                    self.active_tasks[task_id]["status"] = "completed"
                    self.active_tasks[task_id]["output"] = output_file
                    self.active_tasks[task_id]["elapsed"] = elapsed
                
                self.log(f"✅ Task completed! ({elapsed/60:.1f} mins)", task_id)
            else:
                with self.lock:
                    self.active_tasks[task_id]["status"] = "failed"
                    self.active_tasks[task_id]["error"] = "Video merge failed"
                
                self.log(f"❌ Task failed: merge error", task_id)
                
        except Exception as e:
            self.log(f"❌ Task failed: {e}", task_id)
            with self.lock:
                self.active_tasks[task_id]["status"] = "failed"
                self.active_tasks[task_id]["error"] = str(e)
    
    def add_task(self, video_path: str, audio_path: str, text: str = "", task_id: str = None):
        """Add chunked task and start processing"""
        if task_id is None:
            task_id = f"chunked_{int(time.time())}"
        
        self.log(f"📝 New chunked task: {task_id}")
        
        # Start processing in background thread
        thread = threading.Thread(
            target=self.process_chunked_task,
            args=(video_path, audio_path, task_id),
            daemon=True
        )
        thread.start()
        
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
                    response["output"] = task.get("output", "")
                elif task["status"] == "failed":
                    response["error"] = task.get("error", "Unknown error")
                elif task["status"] in ["processing", "splitting", "merging"]:
                    elapsed = time.time() - task["start_time"]
                    response["elapsed_seconds"] = int(elapsed)
                
                return response
            else:
                return {"status": "not_found"}
    
    def get_gpu_status(self) -> Dict:
        """Get current GPU status"""
        with self.lock:
            return {
                "gpu0": "busy" if self.gpu_config[0]["busy"] else "free",
                "gpu1": "busy" if self.gpu_config[1]["busy"] else "free",
                "gpu2": "busy" if self.gpu_config[2]["busy"] else "free",
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
