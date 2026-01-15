#!/usr/bin/env python3
"""
Flask API Server for Triple GPU + Triple TTS Setup
- 3 GPUs (GPU 0 + GPU 1 + GPU 2)
- 3 TTS services (18182 for GPU 0, 18183 for GPU 1, 18184 for GPU 2)
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
    elif tts_port == 18183:
        tts_ref_dir = os.path.expanduser("~/heygem_data/tts1/reference")
    else:  # 18184
        tts_ref_dir = os.path.expanduser("~/heygem_data/tts2/reference")
    
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
        "service": "Triple GPU + Triple TTS Video Generation",
        "version": "1.0.0",
        "port": 5003,
        "gpus": {
            "0": {"video_port": 8390, "tts_port": 18182},
            "1": {"video_port": 8391, "tts_port": 18183},
            "2": {"video_port": 8392, "tts_port": 18184}
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
        
        # Generate task_id with UUID for uniqueness (prevents duplicates in parallel requests)
        import uuid
        task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
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
    print("🚀 Triple GPU + Triple TTS Video Generation API Server")
    print("="*80)
    print("📍 Running on: http://0.0.0.0:5003")
    print("🎬 GPU Configuration:")
    print("   - GPU 0: Video Port 8390, TTS Port 18182 (heygem-tts-dual-0)")
    print("   - GPU 1: Video Port 8391, TTS Port 18183 (heygem-tts-dual-1)")
    print("   - GPU 2: Video Port 8392, TTS Port 18184 (heygem-tts-dual-2)")
    print("🎤 Dedicated TTS per GPU - No bottleneck!")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5003, debug=True, threaded=True)
