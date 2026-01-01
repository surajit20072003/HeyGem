#!/usr/bin/env python3
"""
Intelligent Multi-GPU Video Generation Orchestrator
Automatically handles: Text → Audio → Parallel Video Processing → Merge

Usage:
    python3 multi_gpu_orchestrator.py --video face.mp4 --text "Your text" --output result.mp4
"""
import requests
import subprocess
import time
import os
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import threading
import json
from datetime import datetime
import psutil

class MultiGPUOrchestrator:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.gpu_ports = {
            0: 8390,
            1: 8391,
            2: 8392
        }
        self.gpu_status = {0: 'free', 1: 'free', 2: 'free'}
        self.data_dirs = {
            0: '/root/heygem_data/gpu0/face2face',
            1: '/root/heygem_data/gpu1/face2face',
            2: '/root/heygem_data/gpu2/face2face'
        }
        self.lock = threading.Lock()
    
    def log(self, message: str):
        """Print log message with timestamp"""
        if self.verbose:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {message}")
    
    def text_to_audio(self, text: str, output_file: str) -> float:
        """
        Convert text to audio using TTS
        Returns: audio duration in seconds
        """
        self.log(f"🎤 Generating audio from text ({len(text)} characters)...")
        
        # Try HeyGem TTS service first
        try:
            tts_url = "http://127.0.0.1:18180/tts"
            payload = {"text": text, "output_path": output_file}
            
            response = requests.post(tts_url, json=payload, timeout=60)
            if response.status_code == 200:
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                self.log("   ✅ TTS service used")
            else:
                raise Exception("TTS service failed")
                
        except Exception as e:
            # Fallback: Use gTTS (Google TTS)
            self.log("   ⚠️  TTS service unavailable, using gTTS fallback...")
            tts_start = time.time()
            try:
                from gtts import gTTS
                # Save as MP3 first (gTTS default format)
                temp_mp3 = output_file.replace('.wav', '_temp.mp3')
                # Using tld='co.uk' for British accent (deeper/more masculine)
                # slow=False for normal speed (sounds more natural)
                tts = gTTS(text=text, lang='en', tld='co.uk', slow=False)
                tts.save(temp_mp3)
                
                # Convert MP3 to WAV format
                subprocess.run([
                    'ffmpeg', '-y', '-i', temp_mp3,
                    '-ar', '16000', '-ac', '1',
                    output_file
                ], capture_output=True, check=True)
                
                # Clean up temp MP3
                if os.path.exists(temp_mp3):
                    os.remove(temp_mp3)
                    
            except ImportError:
                self.log("   ⚠️  gTTS not available, using espeak...")
                # Final fallback: espeak
                subprocess.run([
                    'espeak', text, '--stdout', '|',
                    'ffmpeg', '-i', '-', '-ar', '16000', '-ac', '1', output_file
                ], shell=True, check=True)
        
        # Get duration
        duration = self.get_audio_duration(output_file)
        self.log(f"   ✅ Audio generated: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        return duration
    
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
    
    def split_audio(self, audio_file: str, num_chunks: int) -> List[str]:
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
            self.log(f"   Chunk {i+1}/{num_chunks}: {chunk_duration:.1f}s → {output}")
        
        return output_files
    
    def get_free_gpu(self) -> int:
        """Get next free GPU, wait if all busy"""
        while True:
            with self.lock:
                for gpu_id, status in self.gpu_status.items():
                    if status == 'free':
                        self.gpu_status[gpu_id] = 'reserved'
                        return gpu_id
            
            self.log("⏳ All GPUs busy, waiting 10 seconds...")
            time.sleep(10)
    
    def submit_task(self, gpu_id: int, video_file: str, audio_file: str, task_code: str) -> Dict:
        """Submit task to specific GPU"""
        port = self.gpu_ports[gpu_id]
        data_dir = self.data_dirs[gpu_id]
        
        # Create directory if not exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Copy files to GPU's data directory
        video_dest = f"{data_dir}/video_{task_code}.mp4"
        audio_dest = f"{data_dir}/audio_{task_code}.wav"
        
        subprocess.run(['cp', video_file, video_dest], check=True)
        subprocess.run(['cp', audio_file, audio_dest], check=True)
        
        # Submit task
        url = f"http://127.0.0.1:{port}/easy/submit"
        payload = {
            "audio_url": f"/code/data/face2face/audio_{task_code}.wav",
            "video_url": f"/code/data/face2face/video_{task_code}.mp4",
            "code": task_code,
            "chaofen": 0,
            "watermark_switch": 0,
            "pn": 1
        }
        
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()
        
        if result.get('success'):
            with self.lock:
                self.gpu_status[gpu_id] = 'busy'
            self.log(f"✅ Task '{task_code}' → GPU {gpu_id} (Port {port})")
        else:
            self.log(f"❌ Failed to submit task '{task_code}' to GPU {gpu_id}")
        
        return result
    
    def monitor_task(self, gpu_id: int, task_code: str) -> str:
        """Monitor task until completion, returns output file path"""
        port = self.gpu_ports[gpu_id]
        url = f"http://127.0.0.1:{port}/easy/query?code={task_code}"
        
        self.log(f"⏳ Monitoring GPU {gpu_id} - Task '{task_code}'...")
        
        start_time = time.time()
        last_progress = -1
        
        while True:
            try:
                response = requests.get(url, timeout=10)
                data = response.json()
                
                task_data = data.get('data', {})
                progress = task_data.get('progress', 0)
                
                # Log progress changes
                if progress != last_progress and progress > 0:
                    elapsed = time.time() - start_time
                    self.log(f"   GPU {gpu_id}: {progress}% ({elapsed:.0f}s elapsed)")
                    last_progress = progress
                
                # Check if complete by looking for output file
                # Fixed: correct path includes parent 'temp' directory
                output_path = f"{self.data_dirs[gpu_id]}/../temp/{task_code}-r.mp4"
                if os.path.exists(output_path):
                    elapsed = time.time() - start_time
                    with self.lock:
                        self.gpu_status[gpu_id] = 'free'
                    self.log(f"✅ GPU {gpu_id} task '{task_code}' complete! ({elapsed:.0f}s)")
                    return output_path
                
            except Exception as e:
                # Ignore network errors, keep retrying
                pass
            
            time.sleep(10)
    
    def merge_videos(self, video_files: List[str], output_file: str):
        """Merge multiple video chunks using GPU-accelerated FFmpeg"""
        self.log(f"🎬 Merging {len(video_files)} video chunks with GPU acceleration...")
        
        # Create temporary file list for ffmpeg
        list_file = '/tmp/heygem_video_list.txt'
        with open(list_file, 'w') as f:
            for video in video_files:
                f.write(f"file '{video}'\n")
        
        self.log(f"   Using NVIDIA hardware encoding (NVENC)...")
        
        # GPU-accelerated merge using NVENC
        # First concat with demuxer (fast, no re-encoding), then re-encode with GPU if needed
        temp_concat = output_file.replace('.mp4', '_temp_concat.mp4')
        
        # Step 1: Fast concat without re-encoding
        cmd_concat = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            temp_concat
        ]
        
        self.log(f"   Step 1/2: Concatenating chunks...")
        result = subprocess.run(cmd_concat, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.log(f"❌ Concat failed: {result.stderr}")
            raise Exception("Video concatenation failed")
        
        # Step 2: GPU re-encode for optimal quality (optional, can skip for speed)
        # Using h264_nvenc for NVIDIA GPU encoding
        self.log(f"   Step 2/2: GPU encoding final video...")
        cmd_encode = [
            'ffmpeg', '-y',
            '-hwaccel', 'cuda',  # Use CUDA hardware acceleration
            '-i', temp_concat,
            '-c:v', 'h264_nvenc',  # NVIDIA hardware encoder
            '-preset', 'fast',  # Encoding speed preset
            '-b:v', '3M',  # Video bitrate
            '-c:a', 'copy',  # Copy audio without re-encoding
            output_file
        ]
        
        result = subprocess.run(cmd_encode, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.log(f"✅ GPU-accelerated merge complete: {output_file}")
            # Clean up temp file
            if os.path.exists(temp_concat):
                os.remove(temp_concat)
        else:
            # Fallback: if GPU encoding fails, use the concat version
            self.log(f"⚠️  GPU encoding failed, using concatenated version")
            if os.path.exists(temp_concat):
                os.rename(temp_concat, output_file)
                self.log(f"✅ Fallback merge complete: {output_file}")
            else:
                raise Exception("Video merge failed completely")
        
        os.remove(list_file)
    
    def process(self, video_file: str, text: str, output_file: str):
        """
        Main orchestration function
        Handles the complete workflow from text to final merged video
        """
        print("=" * 80)
        print("🚀 Multi-GPU Video Generation Orchestrator")
        print("=" * 80)
        
        # Record start time
        start_time = time.time()
        start_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"⏰ Start Time: {start_datetime}")
        print("=" * 80)
        
        # Step 1: Generate audio from text
        self.log("\n📝 Step 1: Text to Audio Conversion")
        audio_file = '/tmp/generated_audio.wav'
        duration = self.text_to_audio(text, audio_file)
        
        # Step 2: Decide GPU distribution strategy
        # ALWAYS use 3 GPUs by dividing audio into 3 chunks
        duration_minutes = duration / 60
        num_chunks = 3
        strategy = "3 GPUs parallel (forced distribution)"
        
        self.log(f"\n📊 Step 2: Distribution Strategy")
        self.log(f"   Audio duration: {duration_minutes:.2f} minutes ({duration:.1f} seconds)")
        self.log(f"   Strategy: {strategy}")
        self.log(f"   Chunks: {num_chunks}")
        self.log(f"   Each GPU: ~{duration/num_chunks:.1f} seconds")
        
        # Step 3: Split audio into 3 chunks
        self.log(f"\n✂️  Step 3: Audio Preparation")
        self.log(f"   Splitting audio into {num_chunks} equal chunks...")
        audio_chunks = self.split_audio(audio_file, num_chunks)
        
        # Step 4: Process each chunk in parallel
        self.log(f"\n🎬 Step 4: Parallel Video Generation ({num_chunks} tasks)")
        
        tasks = []
        output_videos = []
        
        for i, audio_chunk in enumerate(audio_chunks):
            # Get free GPU (waits if all busy)
            gpu_id = self.get_free_gpu()
            task_code = f"chunk_{i+1:02d}_{int(time.time())}"
            
            # Submit task
            self.submit_task(gpu_id, video_file, audio_chunk, task_code)
            
            # Start monitoring in background thread
            def monitor_wrapper(gpu, code, index):
                output = self.monitor_task(gpu, code)
                with self.lock:
                    output_videos.append((index, output))
            
            thread = threading.Thread(
                target=monitor_wrapper,
                args=(gpu_id, task_code, i)
            )
            thread.start()
            tasks.append(thread)
            
            # Small delay to avoid race conditions
            time.sleep(1)
        
        # Step 5: Wait for all tasks to complete
        self.log(f"\n⏳ Step 5: Waiting for all {num_chunks} tasks to complete...")
        for thread in tasks:
            thread.join()
        
        # Sort videos by chunk index
        output_videos.sort(key=lambda x: x[0])
        sorted_videos = [v[1] for v in output_videos]
        
        # Step 6: Merge if multiple chunks
        self.log(f"\n🎞️  Step 6: Final Video Assembly")
        if num_chunks > 1:
            self.merge_videos(sorted_videos, output_file)
        else:
            subprocess.run(['cp', sorted_videos[0], output_file], check=True)
            self.log(f"✅ Video copied to: {output_file}")
        
        # Calculate total time and get system stats
        total_time = time.time() - start_time
        end_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get RAM usage
        ram = psutil.virtual_memory()
        ram_used_gb = ram.used / (1024**3)
        ram_total_gb = ram.total / (1024**3)
        ram_percent = ram.percent
        
        print("\n" + "=" * 80)
        print("✅ VIDEO GENERATION COMPLETE!")
        print("=" * 80)
        print(f"⏰ Start Time:  {start_datetime}")
        print(f"⏰ End Time:    {end_datetime}")
        print(f"⏱️  Total Time:  {total_time/60:.1f} minutes ({int(total_time)} seconds)")
        print(f"📁 Output File: {output_file}")
        print(f"📊 File Size:   {os.path.getsize(output_file) / (1024*1024):.1f} MB")
        print(f"🧠 RAM Usage:   {ram_used_gb:.1f} GB / {ram_total_gb:.1f} GB ({ram_percent}%)")
        print("=" * 80)
        print("\n🎉 SUCCESS! Your video is ready to download!")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Multi-GPU Video Generation Orchestrator'
    )
    parser.add_argument(
        '--video', '-v',
        required=True,
        help='Input video file (face video)'
    )
    parser.add_argument(
        '--text', '-t',
        required=True,
        help='Text to convert to speech'
    )
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output video file path'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress verbose logging'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.video):
        print(f"❌ Error: Video file not found: {args.video}")
        return 1
    
    # Create orchestrator and process
    orchestrator = MultiGPUOrchestrator(verbose=not args.quiet)
    
    try:
        orchestrator.process(args.video, args.text, args.output)
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
