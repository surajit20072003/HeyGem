#!/usr/bin/env python3
"""
Flask API Server for Dual GPU + Dual TTS Setup
- 2 GPUs (GPU 0 + GPU 1)
- 2 TTS services (18180 for GPU 0, 18181 for GPU 1)
- Port 5003
- Proper queue management
"""
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import subprocess
import time
import threading
from datetime import datetime
from text_normalization import latex_to_speech
from dual_gpu_scheduler import scheduler

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VIDEO_PATH = os.path.join(BASE_DIR, 'default.mp4')
DEFAULT_REFERENCE_AUDIO = os.path.join(BASE_DIR, 'reference_audio.wav')
UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './outputs'
TEMP_FOLDER = './temp'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}


def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


def extract_audio_from_video(video_path: str) -> str:
    """Extract audio from video for voice cloning"""
    output_audio = os.path.join(TEMP_FOLDER, f"ref_audio_{int(time.time())}.wav")
    
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le',
        '-ar', '44100', '-ac', '2',
        output_audio
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return output_audio


def generate_voice_cloning(text: str, reference_audio: str, tts_port: int, task_id: str = None) -> str:
    """
    Generate voice-cloned audio using TTS
    Uses the dedicated TTS service for the assigned GPU
    """
    import requests
    
    tts_start_time = time.time()
    
    TTS_API = f'http://localhost:{tts_port}'
    
    print(f"🎤 Using TTS service on port {tts_port}")
    
    # Clean text
    text = ' '.join(text.split())
    
    if not text or len(text.strip()) == 0:
        print(f"   ❌ Empty text provided, using reference audio as fallback")
        return reference_audio, 0, 0
    
    # Normalize Math/LaTeX if present (matching webapp implementation)
    print(f"   📐 Normalizing Text (Before): {text[:50]}...")
    text = latex_to_speech(text)
    print(f"   📐 Normalizing Text (After):  {text[:50]}...")
    
    # Copy reference audio to TTS data directory (shared volume)
    # Determine which TTS container based on port
    if tts_port == 18182:
        tts_ref_dir = os.path.expanduser("~/heygem_data/tts0/reference")
    else:  # 18183
        tts_ref_dir = os.path.expanduser("~/heygem_data/tts1/reference")
    
    os.makedirs(tts_ref_dir, exist_ok=True)
    
    # FIX: Use unique filename with task_id to prevent race condition
    # Instead of: ref_filename = os.path.basename(reference_audio)
    # This prevents concurrent tasks from overwriting each other's reference audio
    if task_id:
        ref_filename = f"ref_{task_id}_{int(time.time())}.wav"
    else:
        # Fallback if task_id not provided
        ref_filename = f"ref_{int(time.time())}_{os.getpid()}.wav"
    
    tts_ref_path = os.path.join(tts_ref_dir, ref_filename)
    subprocess.run(['cp', reference_audio, tts_ref_path])
    
    print(f"   📁 Copied reference audio to: {tts_ref_path}")
    
    # TTS API call - use invoke directly (no preprocessing needed)
    payload = {
        "text": text,
        "reference_audio": f"/code/data/reference/{ref_filename}",
        "reference_text": "",
        "format": "wav"
    }
    
    try:
        print(f"   Generating voice clone via TTS port {tts_port}...")
        response = requests.post(
            f"{TTS_API}/v1/invoke",
            json=payload,
            timeout=1200 # Increased to 20 minutes to prevent timeout on slower TTS
        )
        
        if response.status_code != 200:
            print(f"   ❌ TTS generation failed: {response.status_code}")
            print(f"   ⚠️  FALLBACK: Using reference audio instead of generated TTS")
            print(f"   ⚠️  Reference audio path: {reference_audio}")
            return reference_audio, 0, 0
        
        # Save generated audio with task_id in filename for easy tracking
        if task_id:
            output_audio = os.path.join(TEMP_FOLDER, f"tts_{task_id}.wav")
        else:
            # Fallback to timestamp if task_id not provided
            output_audio = os.path.join(TEMP_FOLDER, f"tts_output_{int(time.time())}.wav")
        
        with open(output_audio, 'wb') as f:
            f.write(response.content)
        
        # Verify file size
        file_size = os.path.getsize(output_audio)
        if file_size < 10000:  # Less than 10KB is suspicious
            print(f"   ⚠️  Audio too small ({file_size} bytes), using reference audio")
            print(f"   ⚠️  FALLBACK: Using reference audio instead of generated TTS")
            print(f"   ⚠️  Reference audio path: {reference_audio}")
            return reference_audio, 0, 0
        
        # Get audio duration
        duration = get_audio_duration(output_audio)
        
        # Calculate TTS generation time
        tts_time = time.time() - tts_start_time
        
        print(f"   ✓ Voice clone generated: {output_audio} ({file_size} bytes)")
        print(f"   Audio duration: {duration:.2f}s")
        print(f"   ⏱️  TTS generation time: {tts_time:.2f}s")
        
        return output_audio, duration, tts_time
        
    except Exception as e:
        print(f"   ❌ TTS generation error: {e}")
        print(f"   ⚠️  FALLBACK: Using reference audio due to exception")
        print(f"   ⚠️  Reference audio path: {reference_audio}")
        return reference_audio, 0, 0


def get_audio_duration(audio_file: str) -> float:
    """Get audio duration using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


@app.route('/')
def index():
    return send_file('static/index.html')


@app.route('/outputs/<path:filename>')
def serve_output(filename):
    """Serve output files"""
    return send_from_directory(OUTPUT_FOLDER, filename)


@app.route('/api/info')
def api_info():
    """API information"""
    return jsonify({
        "service": "Dual GPU + Dual TTS Video Generation",
        "version": "1.0.0",
        "port": 5003,
        "gpus": {
            "0": {"video_port": 8390, "tts_port": 18180},
            "1": {"video_port": 8391, "tts_port": 18181}
        },
        "endpoints": ["/api/generate", "/api/status", "/api/queue", "/api/download"]
    })


def process_task_background(task_id, text, video_path):
    """Background task with atomic GPU reservation"""
    reserved_gpu_id = None
    
    try:
        # Step 1: Extract or use default reference audio
        if video_path:
            scheduler.set_preprocessing_status(task_id, "Extracting audio from video...")
            print(f"\n🎬 [Task {task_id}] Extracting audio from video...")
            
            reference_audio = extract_audio_from_video(video_path)
            print(f"   ✓ Audio extracted: {reference_audio}")
        else:
            # Use default reference audio
            if os.path.exists(DEFAULT_REFERENCE_AUDIO):
                reference_audio = DEFAULT_REFERENCE_AUDIO
                print(f"\n🎵 [Task {task_id}] Using default reference audio: {reference_audio}")
            else:
                print(f"❌ [Task {task_id}] No reference audio available")
                scheduler.clear_preprocessing_status(task_id)
                with scheduler.lock:
                    scheduler.active_tasks[task_id] = {
                        "status": "failed",
                        "error": "No reference audio available",
                        "timestamp": datetime.now()
                    }
                return
        
        # Step 2: RESERVE GPU FIRST (atomic operation)
        scheduler.set_preprocessing_status(task_id, "Reserving GPU...")
        print(f"\n🔐 [Task {task_id}] Attempting to reserve GPU...")
        
        reserved_gpu_id = scheduler.reserve_gpu_for_task(task_id)
        
        if reserved_gpu_id is None:
            # All GPUs busy, add to queue
            print(f"⏸️  [Task {task_id}] All GPUs busy, adding to queue...")
            
            # Use default video if needed
            if not video_path:
                video_path = DEFAULT_VIDEO_PATH
            
            # Add to queue with already-extracted audio
            scheduler.add_to_queue_only(
                task_id=task_id,
                video_path=video_path,
                audio_path=reference_audio,
                text=text
            )
            scheduler.clear_preprocessing_status(task_id)
            return
        
        # Step 3: GPU reserved! Use its dedicated TTS port
        tts_port = scheduler.gpu_config[reserved_gpu_id]["tts_port"]
        
        scheduler.set_preprocessing_status(
            task_id, 
            f"Generating voice on GPU {reserved_gpu_id} (TTS port {tts_port})..."
        )
        print(f"\n🎤 [Task {task_id}] GPU {reserved_gpu_id} reserved, generating voice clone using TTS {tts_port}...")
        
        cloned_audio, duration, tts_time = generate_voice_cloning(text, reference_audio, tts_port, task_id)
        print(f"   ✓ Voice clone ready: {cloned_audio} ({duration:.2f}s)")
        
        # Store TTS timing and audio info in task metadata
        with scheduler.lock:
            if task_id in scheduler.active_tasks:
                scheduler.active_tasks[task_id]["tts_time"] = tts_time
                scheduler.active_tasks[task_id]["input_text"] = text
                scheduler.active_tasks[task_id]["reference_audio"] = reference_audio
                scheduler.active_tasks[task_id]["generated_audio"] = cloned_audio
        
        # Step 4: Clear preprocessing status
        scheduler.clear_preprocessing_status(task_id)
        
        # Use default video if no video uploaded
        if not video_path:
            video_path = DEFAULT_VIDEO_PATH
            print(f"   📹 Using default video: {video_path}")
        
        # Step 5: Submit to the SAME reserved GPU
        print(f"\n📋 [Task {task_id}] Submitting to reserved GPU {reserved_gpu_id}...")
        
        success = scheduler.submit_to_gpu(
            video_path=video_path,
            audio_path=cloned_audio,
            task_id=task_id,
            gpu_id=reserved_gpu_id  # Use the reserved GPU
        )
        
        if not success:
            # Submission failed, release GPU
            print(f"❌ [Task {task_id}] Submission failed, releasing GPU {reserved_gpu_id}")
            scheduler.release_gpu(reserved_gpu_id, task_id)
            
            # Mark as failed
            with scheduler.lock:
                scheduler.active_tasks[task_id]["status"] = "failed"
                scheduler.active_tasks[task_id]["error"] = "GPU submission failed"
        else:
            print(f"   ✓ Task submitted successfully to GPU {reserved_gpu_id}")
        
    except Exception as e:
        print(f"❌ [Task {task_id}] Error in background processing: {e}")
        import traceback
        traceback.print_exc()
        
        # Release GPU if it was reserved
        if reserved_gpu_id is not None:
            print(f"   Releasing GPU {reserved_gpu_id} due to error")
            scheduler.release_gpu(reserved_gpu_id, task_id)
        
        scheduler.clear_preprocessing_status(task_id)
        
        # Mark task as failed
        with scheduler.lock:
            scheduler.active_tasks[task_id] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now()
            }


def process_queued_task_with_tts(task_data, gpu_id):
    """
    Process a queued task by generating TTS and then submitting to the reserved GPU.
    Called when a task is dequeued and GPU is already reserved.
    """
    task_id = task_data["task_id"]
    text = task_data.get("text", "")
    reference_audio = task_data["audio_path"]  # This is the reference audio
    video_path = task_data["video_path"]
    
    try:
        print(f"\n🎤 [Queued Task {task_id}] Generating TTS on reserved GPU {gpu_id}...")
        
        # Get TTS port for reserved GPU
        tts_port = scheduler.gpu_config[gpu_id]["tts_port"]
        print(f"   Using TTS port {tts_port} for GPU {gpu_id}")
        print(f"   Text: {text[:100]}..." if len(text) > 100 else f"   Text: {text}")
        
        # Generate TTS
        cloned_audio, duration, tts_time = generate_voice_cloning(text, reference_audio, tts_port, task_id)
        print(f"   ✓ Voice clone generated: {cloned_audio} ({duration:.2f}s)")
        
        # Store TTS timing and audio info in task metadata
        with scheduler.lock:
            if task_id in scheduler.active_tasks:
                scheduler.active_tasks[task_id]["tts_time"] = tts_time
                scheduler.active_tasks[task_id]["input_text"] = text
                scheduler.active_tasks[task_id]["reference_audio"] = reference_audio
                scheduler.active_tasks[task_id]["generated_audio"] = cloned_audio
        
        # Submit to the reserved GPU
        print(f"\n📤 [Queued Task {task_id}] Submitting to GPU {gpu_id}...")
        success = scheduler.submit_to_gpu(
            video_path=video_path,
            audio_path=cloned_audio,  # Use generated TTS audio
            task_id=task_id,
            gpu_id=gpu_id
        )
        
        if not success:
            # Submission failed, release GPU
            print(f"❌ [Queued Task {task_id}] Submission failed, releasing GPU {gpu_id}")
            scheduler.release_gpu(gpu_id, task_id)
            
            # Mark as failed
            with scheduler.lock:
                scheduler.active_tasks[task_id]["status"] = "failed"
                scheduler.active_tasks[task_id]["error"] = "GPU submission failed after TTS"
        else:
            print(f"   ✓ Successfully submitted to GPU {gpu_id}")
    
    except Exception as e:
        print(f"❌ [Queued Task {task_id}] Error processing: {e}")
        import traceback
        traceback.print_exc()
        
        # Release GPU
        scheduler.release_gpu(gpu_id, task_id)
        
        # Mark as failed
        with scheduler.lock:
            scheduler.active_tasks[task_id]["status"] = "failed"
            scheduler.active_tasks[task_id]["error"] = f"TTS generation failed: {str(e)}"


# Register the callback with scheduler
scheduler.queued_task_processor = process_queued_task_with_tts


@app.route('/api/generate', methods=['POST'])

def generate_video():
    """
    Generate video with voice cloning
    Input: video file (optional) + text
    Output: task_id immediately
    """
    try:
        # Check if text provided
        if 'text' not in request.form:
            return jsonify({"error": "No text provided"}), 400
        
        text = request.form.get('text', '')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Generate task_id
        task_id = f"task_{int(time.time())}"
        
        # Check if video file is present (optional now)
        video_path = None
        if 'video' in request.files:
            video_file = request.files['video']
            
            if video_file.filename == '':
                print(f"   ⚠️ Empty video filename, will use default")
            elif not allowed_video_file(video_file.filename):
                return jsonify({"error": "Invalid video format"}), 400
            else:
                # Save video file
                video_filename = f"{task_id}_{video_file.filename}"
                video_path = os.path.join(UPLOAD_FOLDER, video_filename)
                video_file.save(video_path)
                print(f"   ✅ Video uploaded: {video_file.filename}")
        
        if not video_path:
            print(f"   📹 No video uploaded - will use default video + default reference audio")
        
        print(f"\n{'='*80}")
        print(f"📥 New Task: {task_id}")
        print(f"   Video: {os.path.basename(video_path) if video_path else 'DEFAULT'}")
        print(f"   Text: {text[:100]}..." if len(text) > 100 else f"   Text: {text}")
        print(f"{'='*80}")
        
        # Initialize task in preprocessing
        scheduler.set_preprocessing_status(task_id, "Task received, starting preprocessing...")
        
        # Start background processing (audio extraction + TTS + queue)
        bg_thread = threading.Thread(
            target=process_task_background,
            args=(task_id, text, video_path),
            daemon=True
        )
        bg_thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "Task submitted successfully",
            "status_url": f"/api/status/{task_id}"
        }), 202
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """Get task status"""
    status = scheduler.get_task_status(task_id)
    return jsonify(status)


@app.route('/api/download/<task_id>')
def download_video(task_id):
    """Download generated video"""
    # TODO: Implement proper file path retrieval from task result
    output_path = os.path.join(OUTPUT_FOLDER, f"{task_id}_output.mp4")
    
    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True)
    else:
        return jsonify({"error": "Video not found"}), 404


@app.route('/api/queue')
def get_queue():
    """Get current task queue status"""
    gpu_status = scheduler.get_gpu_status()
    
    # Get queue list
    queue_list = []
    for task_data in list(scheduler.task_queue.queue):
        queue_list.append({
            "task_id": task_data["task_id"],
            "queued_time": task_data["queued_time"].isoformat(),
            "text": task_data["text"][:50] + "..." if len(task_data["text"]) > 50 else task_data["text"]
        })
    
    return jsonify({
        "gpus": gpu_status,
        "queue": queue_list,
        "queue_size": len(queue_list)
    })


@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "service": "Dual GPU + Dual TTS",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 Dual GPU + Dual TTS Video Generation API Server")
    print("="*80)
    print("📍 Running on: http://0.0.0.0:5003")
    print("🎬 GPU Configuration:")
    print("   - GPU 0: Video Port 8390, TTS Port 18182 (heygem-tts-dual-0)")
    print("   - GPU 1: Video Port 8391, TTS Port 18183 (heygem-tts-dual-1)")
    print("🎤 Dedicated TTS per GPU - No bottleneck!")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5003, debug=True, threaded=True)




#!/usr/bin/env python3
"""
Dual GPU Scheduler with Dedicated TTS Containers
- GPU 0 (Port 8390) → TTS 0 (Port 18180)
- GPU 1 (Port 8391) → TTS 1 (Port 18181)
- Proper queue management
- No GPU 2 usage
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
        # 2 GPUs with dedicated TTS services
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
            }
        }
        
        # Task management
        self.task_queue = Queue()
        self.active_tasks = {}  # task_id -> {status, gpu_id, progress, ...}
        self.preprocessing_tasks = {}  # Tasks in audio extraction/TTS phase
        
        # Threading
        self.lock = threading.Lock()
        
        print("🚀 Dual GPU Scheduler Initialized")
        print(f"   GPU 0: Video Port {self.gpu_config[0]['port']}, TTS Port {self.gpu_config[0]['tts_port']} (heygem-tts-dual-0)")
        print(f"   GPU 1: Video Port {self.gpu_config[1]['port']}, TTS Port {self.gpu_config[1]['tts_port']} (heygem-tts-dual-1)")

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
        Find first free GPU (0 or 1)
        Returns: GPU ID or None if both busy
        """
        with self.lock:
            for gpu_id in [0, 1]:  # Only GPU 0 and 1
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
            for gpu_id in [0, 1]:
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
            for gid in [0, 1]:
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
    print("🚀 Dual GPU Scheduler with Dedicated TTS Services")
    print("=" * 80)
    print("GPU 0 (Port 8390) → TTS (Port 18182) [heygem-tts-dual-0]")
    print("GPU 1 (Port 8391) → TTS (Port 18183) [heygem-tts-dual-1]")
    print("=" * 80)
