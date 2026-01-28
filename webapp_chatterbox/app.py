#!/usr/bin/env python3
"""
Flask API Server for Triple GPU + Chatterbox TTS Setup
- 3 GPUs (GPU 0 + GPU 1 + GPU 2)
- 3 Chatterbox TTS services (20182 for GPU 0, 20183 for GPU 1, 20184 for GPU 2)
- Port 5004
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
from chatterbox_scheduler import scheduler
from library_manager import LibraryManager

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VIDEO_PATH = os.path.join(BASE_DIR, 'default.mp4')
DEFAULT_REFERENCE_AUDIO = os.path.join(BASE_DIR, 'reference_audio.wav')
UPLOAD_FOLDER = os.path.abspath('./uploads')
OUTPUT_FOLDER = os.path.abspath('./outputs')
TEMP_FOLDER = os.path.abspath('./temp')

# Initialize Library Manager
lib_manager = LibraryManager(BASE_DIR)

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
    
    # Chatterbox uses direct file paths (no Docker volume mapping)
    # Simply pass the reference audio path directly
    print(f"   📁 Using reference audio: {reference_audio}")
    
    # Chatterbox TTS API call
    payload = {
        "text": text,
        "reference_audio": reference_audio,  # Direct file path
        "format": "wav"
    }
    
    try:
        print(f"   Generating voice clone via TTS port {tts_port}...")
        response = requests.post(
            f"{TTS_API}/v1/invoke",
            json=payload,
            timeout=5000 # Increased to 20 minutes to prevent timeout on slower TTS
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
        
        # UNLOAD MODEL TO FREE GPU MEMORY
        try:
            print(f"   🧹 Unloading TTS model from port {tts_port}...")
            requests.post(f"{TTS_API}/v1/unload", timeout=10)
        except Exception as e:
            print(f"   ⚠️  Failed to unload model: {e}")
        
        return output_audio, duration, tts_time
        
    except Exception as e:
        print(f"   ❌ TTS generation error: {e}")
        print(f"   ⚠️  FALLBACK: Using reference audio due to exception")
        
        # Still try to unload model in case of error
        try:
            requests.post(f"{TTS_API}/v1/unload", timeout=10)
        except:
            pass
            
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
        "service": "Triple GPU + Chatterbox TTS Video Generation",
        "tts_engine": "Chatterbox-Turbo (Resemble AI)",
        "version": "1.0.0",
        "port": 5004,
        "gpus": {
            "0": {"video_port": 8390, "tts_port": 20182},
            "1": {"video_port": 8391, "tts_port": 20183},
            "2": {"video_port": 8392, "tts_port": 20184}
        },
        "features": [
            "Zero-shot voice cloning",
            "Multilingual support (23 languages)",
            "Paralinguistic tags ([laugh], [cough], [chuckle])",
            "Ultra-low latency (~200ms)"
        ],
        "endpoints": ["/api/generate", "/api/status", "/api/queue", "/api/download"]
    })


def process_task_background(task_id, text, video_path, audio_path=None):
    """Background task with atomic GPU reservation"""
    reserved_gpu_id = None
    
    try:
        # Step 1: Extract or use default reference audio
        reference_audio = None
        
        if audio_path:
             # Use explicit audio path (e.g. from Library)
             reference_audio = audio_path
             print(f"\n🎵 [Task {task_id}] Using provided reference audio: {reference_audio}")
             
        elif video_path:
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
                scheduler.active_tasks[task_id]["audio_duration"] = duration
        
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
                scheduler.active_tasks[task_id]["audio_duration"] = duration
        
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
        
        # Check for Avatar ID (Overwrites video_path if valid)
        avatar_id = request.form.get('avatar_id')
        audio_path = None # Explicit audio path
        
        if avatar_id:
            print(f"   👤 Avatar ID provided: {avatar_id}")
            lib_video, lib_audio = lib_manager.get_avatar_paths(avatar_id)
            if lib_video and lib_audio:
                video_path = lib_video
                audio_path = lib_audio 
                print(f"   ✅ Found avatar assets: {os.path.basename(video_path)}")
                print(f"   ✅ Using stored audio: {os.path.basename(audio_path)}")
            else:
                 return jsonify({"error": "id not match"}), 400

        if not video_path:
            print(f"   📹 No input provided - Using DEFAULTS")
            video_path = DEFAULT_VIDEO_PATH
            audio_path = DEFAULT_REFERENCE_AUDIO
        
        print(f"\n{'='*80}")
        print(f"📥 New Task: {task_id}")
        print(f"   Video: {os.path.basename(video_path) if video_path else 'DEFAULT'}")
        print(f"   Audio: {os.path.basename(audio_path) if audio_path else 'Auot-Extract'}")
        print(f"   Text: {text[:100]}..." if len(text) > 100 else f"   Text: {text}")
        print(f"{'='*80}")
        
        # Initialize task in preprocessing
        scheduler.set_preprocessing_status(task_id, "Task received, starting preprocessing...")
        
        # Start background processing (audio extraction + TTS + queue)
        bg_thread = threading.Thread(
            target=process_task_background,
            args=(task_id, text, video_path, audio_path),
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


@app.route('/api/download/audio/<task_id>')
def download_audio(task_id):
    """Download generated audio"""
    filename = f"tts_{task_id}.wav"
    file_path = os.path.join(TEMP_FOLDER, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "Audio file not found"}), 404


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


@app.route('/api/history')
def get_history():
    """Get all tasks history (completed, failed, processing, timeout)"""
    with scheduler.lock:
        tasks = []
        for task_id, task_data in scheduler.active_tasks.items():
            # Check if audio file exists and create download link
            audio_url = None
            if task_data.get("generated_audio") and os.path.exists(task_data.get("generated_audio")):
                audio_url = f"/api/download/audio/{task_id}"

            # Check if video file exists locally
            video_url = task_data.get("result", {}).get("data", {}).get("result_url")
            local_video_path = os.path.join(OUTPUT_FOLDER, f"{task_id}_output.mp4")
            if os.path.exists(local_video_path):
                video_url = f"/api/download/{task_id}"

            task_info = {
                "task_id": task_id,
                "status": task_data.get("status", "unknown"),
                "start_time": task_data.get("start_time").isoformat() if task_data.get("start_time") else None,
                "completed_time": task_data.get("completed_time").isoformat() if task_data.get("completed_time") else None,
                "gpu_id": task_data.get("gpu_id"),
                "input_text": task_data.get("input_text", "")[:200],  # Truncate for list view
                "reference_audio": task_data.get("reference_audio"),
                "generated_audio_url": audio_url,
                "audio_duration": task_data.get("audio_duration", 0),
                "error": task_data.get("error"),
                "progress": task_data.get("progress", 0),
                "timing": {
                    "tts_time": task_data.get("tts_time"),
                    "video_time": task_data.get("video_time"),
                    "total_time": task_data.get("total_time")
                },
                "vimeo_url": task_data.get("vimeo_url"),
                "vimeo_uploaded": task_data.get("vimeo_uploaded", False),
                "result_url": video_url
            }
            tasks.append(task_info)

        
        # Sort by start_time (newest first)
        tasks.sort(key=lambda x: x.get("start_time") or "", reverse=True)
        
    return jsonify({
        "total": len(tasks),
        "tasks": tasks
    })



@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "service": "Triple GPU + Chatterbox TTS",
        "timestamp": datetime.now().isoformat()
    })


# --- Library API Endpoints ---

@app.route('/api/library/upload', methods=['POST'])
def library_upload():
    """Upload new avatar to library"""
    try:
        if 'video' not in request.files:
            return jsonify({"error": "No video file provided"}), 400
            
        video_file = request.files['video']
        name = request.form.get('name', 'Untitled Avatar')
        
        if video_file.filename == '':
            return jsonify({"error": "Empty filename"}), 400
            
        # Save to temp first
        temp_filename = f"lib_upload_{int(time.time())}_{video_file.filename}"
        temp_video_path = os.path.join(TEMP_FOLDER, temp_filename)
        video_file.save(temp_video_path)
        
        # Audio Handling: Check if explicit audio provided
        temp_audio_path = None
        if 'audio' in request.files and request.files['audio'].filename != '':
            audio_file = request.files['audio']
            temp_audio_name = f"lib_upload_audio_{int(time.time())}_{audio_file.filename}"
            temp_audio_path = os.path.join(TEMP_FOLDER, temp_audio_name)
            audio_file.save(temp_audio_path)
            print(f"   🎤 Using explicit reference audio: {audio_file.filename}")
        else:
            # Extract audio from video
            try:
                print(f"   🎤 Extracting audio from video...")
                temp_audio_path = extract_audio_from_video(temp_video_path)
            except Exception as e:
                # Cleanup video if audio fails
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                return jsonify({"error": f"Audio extraction failed: {str(e)}"}), 500
            
        # Add to library
        result = lib_manager.add_avatar(temp_video_path, temp_audio_path, name)
        
        # Cleanup temp files
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/library/list', methods=['GET'])
def library_list():
    """List all avatars"""
    return jsonify({
        "avatars": lib_manager.list_avatars()
    })

@app.route('/api/library/delete/<avatar_id>', methods=['DELETE'])
def library_delete(avatar_id):
    """Delete avatar"""
    success = lib_manager.delete_avatar(avatar_id)
    return jsonify({"success": success})

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 Triple GPU + Chatterbox TTS Video Generation API Server")
    print("="*80)
    print("📍 Running on: http://0.0.0.0:5004")
    print("🎬 GPU Configuration:")
    print("   - GPU 0: Video Port 8390, Chatterbox TTS Port 20182")
    print("   - GPU 1: Video Port 8391, Chatterbox TTS Port 20183")
    print("   - GPU 2: Video Port 8392, Chatterbox TTS Port 20184")
    print("🎤 Chatterbox-Turbo: Zero-shot voice cloning with ultra-low latency!")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5004, debug=True, threaded=True)
    