#!/usr/bin/env python3
"""
Multi-Video Random Merge Scheduler - 3 GPU Parallel Processing
Randomly merges multiple input videos per chunk for natural variation
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


class MultiVideoScheduler:
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
        self.active_tasks = {}
        self.lock = threading.Lock()
        
    def log(self, message: str, task_id: str = ""):
        """Thread-safe logging"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefix = f"[{task_id}] " if task_id else ""
        print(f"[{timestamp}] {prefix}{message}")
    
    def get_video_duration(self, video_file: str) -> float:
        """Get video duration using ffprobe"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    
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
    
    def merge_videos_randomly(self, video_files: List[str], target_duration: float, output_path: str) -> str:
        """
        Simple random merge: Pick random FULL videos until total >= target
        HeyGen API will auto-trim video to match audio duration
        """
        self.log(f"🎲 Random video selection (target: {target_duration:.1f}s)...")
        
        # Get all video info
        video_pool = []
        for video in video_files:
            duration = self.get_video_duration(video)
            video_pool.append({"path": video, "duration": duration})
            self.log(f"   Available: {os.path.basename(video)} ({duration:.1f}s)")
        
        # Randomly select FULL videos until we have enough duration
        selected = []
        total_duration = 0.0
        
        while total_duration < target_duration:
            # Pick random video from pool
            if not video_pool:
                # Ran out of videos, start over from beginning
                video_pool = [{"path": v["path"], "duration": self.get_video_duration(v["path"])} 
                             for v in selected]  # Reuse already selected
                if not video_pool:
                    break
            
            random_video = random.choice(video_pool)
            video_pool.remove(random_video)
            
            selected.append(random_video["path"])
            total_duration += random_video["duration"]
            
            self.log(f"   ✅ Selected: {os.path.basename(random_video['path'])} ({random_video['duration']:.1f}s)")
            self.log(f"      Total so far: {total_duration:.1f}s / {target_duration:.1f}s")
        
        self.log(f"   📊 Final: {len(selected)} video(s), {total_duration:.1f}s total")
        self.log(f"   ℹ️  HeyGen will auto-trim to {target_duration:.1f}s")
        
        # If only one video selected and it's >= target, just use it directly
        if len(selected) == 1:
            self.log(f"   🎯 Using single video directly")
            return selected[0]
        
        # Concatenate multiple videos
        concat_file = output_path.replace('.mp4', '_concat.txt')
        with open(concat_file, 'w') as f:
            for video_path in selected:
                f.write(f"file '{video_path}'\n")
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.remove(concat_file)
        
        if result.returncode == 0:
            actual_duration = self.get_video_duration(output_path)
            self.log(f"   ✅ Merged video: {actual_duration:.1f}s")
            return output_path
        else:
            self.log(f"   ❌ Merge failed: {result.stderr[:200]}")
            return None
    
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
        
        os.makedirs(gpu_data_dir, exist_ok=True)
        
        try:
            # Copy files to GPU directory
            subprocess.run(['cp', video_path, gpu_data_dir], check=True)
            subprocess.run(['cp', audio_path, gpu_data_dir], check=True)
            
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
        """Monitor chunk task until completion"""
        output_path = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/temp/{task_code}-r.mp4")
        
        self.log(f"🔍 Monitoring GPU {gpu_id} - Task '{task_code}'")
        
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
                
                with self.lock:
                    self.gpu_config[gpu_id]["busy"] = False
                
                self.log(f"✅ GPU {gpu_id} chunk complete! ({elapsed:.0f}s, {current_size/1024/1024:.1f} MB)")
                return output_path
            
            time.sleep(5)
    
    def merge_final_videos(self, video_files: List[str], output_file: str) -> bool:
        """Merge final video chunks with resolution normalization"""
        self.log(f"🎬 Merging {len(video_files)} final chunks...")
        
        # Step 1: Get resolutions of all chunks
        resolutions = []
        for video in video_files:
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                   '-show_entries', 'stream=width,height',
                   '-of', 'csv=p=0', video]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                w, h = result.stdout.strip().split(',')
                resolutions.append((int(w), int(h)))
                self.log(f"   {os.path.basename(video)}: {w}x{h}")
        
        # Step 2: Find most common resolution or use first
        target_res = resolutions[0] if resolutions else (544, 736)
        self.log(f"   Target resolution: {target_res[0]}x{target_res[1]}")
        
        # Step 3: Scale all videos to same resolution
        scaled_videos = []
        for i, video in enumerate(video_files):
            if resolutions[i] == target_res:
                # Already correct resolution, use directly
                scaled_videos.append(video)
                self.log(f"   ✓ Chunk {i+1}: Same resolution, no scaling needed")
            else:
                # Need to scale
                scaled_path = video.replace('-r.mp4', f'-scaled.mp4')
                cmd = [
                    'ffmpeg', '-y',
                    '-hwaccel', 'cuda',  # GPU acceleration
                    '-i', video,
                    '-vf', f'scale={target_res[0]}:{target_res[1]}',
                    '-c:v', 'h264_nvenc',  # GPU encoding (FAST!)
                    '-preset', 'fast',
                    '-b:v', '3M',
                    '-c:a', 'copy',
                    scaled_path
                ]
                self.log(f"   🔄 Chunk {i+1}: Scaling {resolutions[i][0]}x{resolutions[i][1]} → {target_res[0]}x{target_res[1]}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    scaled_videos.append(scaled_path)
                else:
                    self.log(f"   ⚠️  Scaling failed for chunk {i+1}, using original")
                    scaled_videos.append(video)
        
        # Step 4: Create concat list with scaled videos
        list_file = '/tmp/heygem_multi_video_list.txt'
        with open(list_file, 'w') as f:
            for video in scaled_videos:
                f.write(f"file '{video}'\n")
        
        temp_concat = output_file.replace('.mp4', '_temp.mp4')
        
        # Step 5: Concatenate with matching resolutions
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            temp_concat
        ]
        
        self.log("   📹 Concatenating chunks...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.log(f"   ❌ Concat failed: {result.stderr[:200]}")
            os.remove(list_file)
            return False
        
        # Step 6: GPU encode final video
        cmd = [
            'ffmpeg', '-y',
            '-hwaccel', 'cuda',
            '-i', temp_concat,
            '-c:v', 'h264_nvenc',
            '-preset', 'fast',
            '-b:v', '3M',
            '-c:a', 'copy',
            output_file
        ]
        
        self.log("   🚀 GPU encoding final video...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.log(f"✅ Final merge complete!")
            if os.path.exists(temp_concat):
                os.remove(temp_concat)
        else:
            if os.path.exists(temp_concat):
                os.rename(temp_concat, output_file)
        
        os.remove(list_file)
        return os.path.exists(output_file)
    
    def process_multi_video_task(self, input_videos: List[str], audio_path: str, task_id: str):
        """Main workflow with random video merging"""
        try:
            self.log(f"🚀 Starting multi-video processing", task_id)
            
            with self.lock:
                self.active_tasks[task_id] = {
                    "status": "splitting",
                    "chunks": [],
                    "start_time": time.time()
                }
            
            # Step 1: Split audio
            audio_chunks = self.split_audio(audio_path, num_chunks=3)
            
            # Step 2: Create random merged videos for each chunk
            self.log(f"🎲 Creating random video merges for each chunk", task_id)
            
            merged_videos = []
            for i, audio_chunk in enumerate(audio_chunks):
                chunk_duration = self.get_audio_duration(audio_chunk)
                merged_video_path = f"/nvme0n1-disk/HeyGem/webapp_multi_video/temp/merged_chunk{i+1}_{task_id}.mp4"
                
                merged_video = self.merge_videos_randomly(
                    input_videos,
                    chunk_duration,
                    merged_video_path
                )
                
                if not merged_video:
                    self.log(f"❌ Failed to merge videos for chunk {i+1}", task_id)
                    with self.lock:
                        self.active_tasks[task_id]["status"] = "failed"
                        self.active_tasks[task_id]["error"] = f"Video merge failed for chunk {i+1}"
                    return
                
                merged_videos.append(merged_video)
            
            # Step 3: Submit to GPUs
            self.log(f"🎬 Submitting 3 chunks to GPUs", task_id)
            
            chunk_tasks = []
            chunk_outputs = []
            
            for i, (merged_video, audio_chunk) in enumerate(zip(merged_videos, audio_chunks)):
                gpu_id = i
                chunk_code = f"{task_id}_chunk{i+1:02d}"
                
                success = self.submit_to_gpu(gpu_id, merged_video, audio_chunk, chunk_code)
                
                if not success:
                    self.log(f"❌ Failed to submit chunk {i+1}", task_id)
                    with self.lock:
                        self.active_tasks[task_id]["status"] = "failed"
                        self.active_tasks[task_id]["error"] = f"Chunk {i+1} submission failed"
                    return
                
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
                time.sleep(0.5)
            
            with self.lock:
                self.active_tasks[task_id]["status"] = "processing"
                self.active_tasks[task_id]["chunks"] = [
                    {"gpu_id": i, "status": "processing"} for i in range(3)
                ]
            
            # Step 4: Wait for completion
            self.log(f"⏳ Waiting for all chunks", task_id)
            for thread in chunk_tasks:
                thread.join()
            
            chunk_outputs.sort(key=lambda x: x[0])
            sorted_videos = [v[1] for v in chunk_outputs]
            
            # Step 5: Final merge
            with self.lock:
                self.active_tasks[task_id]["status"] = "merging"
            
            output_file = f"/nvme0n1-disk/HeyGem/webapp_multi_video/outputs/output_{task_id}.mp4"
            merge_success = self.merge_final_videos(sorted_videos, output_file)
            
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
                    self.active_tasks[task_id]["error"] = "Final merge failed"
                
                self.log(f"❌ Task failed: merge error", task_id)
                
        except Exception as e:
            self.log(f"❌ Task failed: {e}", task_id)
            with self.lock:
                self.active_tasks[task_id]["status"] = "failed"
                self.active_tasks[task_id]["error"] = str(e)
    
    def add_task(self, input_videos: List[str], audio_path: str, task_id: str = None):
        """Add multi-video task"""
        if task_id is None:
            task_id = f"multi_{int(time.time())}"
        
        self.log(f"📝 New multi-video task: {task_id}")
        self.log(f"   Input videos: {len(input_videos)}")
        
        thread = threading.Thread(
            target=self.process_multi_video_task,
            args=(input_videos, audio_path, task_id),
            daemon=True
        )
        thread.start()
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict:
        """Get task status"""
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
        """Get GPU status"""
        with self.lock:
            return {
                "gpu0": "busy" if self.gpu_config[0]["busy"] else "free",
                "gpu1": "busy" if self.gpu_config[1]["busy"] else "free",
                "gpu2": "busy" if self.gpu_config[2]["busy"] else "free",
                "active_tasks": len([t for t in self.active_tasks.values() 
                                   if t["status"] in ["splitting", "processing", "merging"]])
            }


# Global scheduler instance
scheduler = MultiVideoScheduler()


if __name__ == "__main__":
    print("🚀 Multi-Video Random Merge Scheduler")
    print("=" * 80)
    print("Randomly merges multiple input videos for natural variation")
    print("=" * 80)
