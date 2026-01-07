#!/usr/bin/env python3
"""
Flask API Server for Multi-GPU Video Generation
Handles video upload, TTS voice cloning, and GPU scheduling
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import subprocess
import time
from werkzeug.utils import secure_filename
from gpu_scheduler import scheduler
from text_normalization import latex_to_speech

app = Flask(__name__)
CORS(app)

import threading

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Default video path
DEFAULT_VIDEO_PATH = os.path.join(BASE_DIR, 'default.mp4')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
TEMP_FOLDER = os.path.join(BASE_DIR, 'temp')
TTS_API = 'http://localhost:18181'  # New working Fish-Speech container

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def extract_audio_from_video(video_path: str) -> str:
    """Extract audio from video for voice cloning"""
    audio_output = os.path.join(TEMP_FOLDER, f"ref_audio_{int(time.time())}.wav")
    
    try:
        # Extract audio using ffmpeg, limit to 15 seconds for better TTS stability
        cmd = ['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', '-t', '15', audio_output]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return audio_output
    except Exception as e:
        print(f"❌ Audio extraction error: {e}")
        return None

def generate_voice_cloning(text: str, reference_audio: str) -> str:
    """Generate voice-cloned audio using TTS"""
    import requests
    
    # Clean text
    text = ' '.join(text.split())
    
    if not text or len(text.strip()) == 0:
        print(f"   ❌ Empty text provided, using reference audio as fallback")
        return reference_audio
    
    print(f"   📝 TTS Request: '{text[:80]}...' ({len(text)} chars)")
    
    # Copy reference audio to TTS data directory
    tts_ref_dir = os.path.expanduser("~/heygem_data/tts/reference")
    os.makedirs(tts_ref_dir, exist_ok=True)
    
    ref_filename = os.path.basename(reference_audio)
    tts_ref_path = os.path.join(tts_ref_dir, ref_filename)
    subprocess.run(['cp', reference_audio, tts_ref_path])
    
    # TTS API call
    # Normalize Math/LaTeX if present
    print(f"   📐 Normalizing Text (Before): {text[:50]}...")
    text = latex_to_speech(text)
    print(f"   📐 Normalizing Text (After):  {text[:50]}...")

    payload = {
        "text": text,
        "reference_audio": f"/code/data/reference/{ref_filename}",
        "reference_text": "",
        "format": "wav"
    }
    
    try:
        response = requests.post(
            f"{TTS_API}/v1/invoke",
            json=payload,
            timeout=6000 # Increased timeout for long text
        )
        
        print(f"   Status: {response.status_code}, Size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            # Save generated audio
            output_audio = os.path.join(TEMP_FOLDER, f"cloned_audio_{int(time.time())}.wav")
            with open(output_audio, 'wb') as f:
                f.write(response.content)
            
            # Verify file size (should be > 10KB for valid audio)
            file_size = os.path.getsize(output_audio)
            if file_size < 10000:  # Less than 10KB is suspicious
                print(f"   ⚠️  Audio too small ({file_size} bytes), using reference audio")
                return reference_audio
            
            print(f"   ✅ Generated audio: {file_size} bytes")
            return output_audio
        else:
            print(f"   ❌ TTS error: {response.status_code}")
            return reference_audio
            
    except Exception as e:
        print(f"   ❌ TTS request error: {e}")
        return reference_audio


@app.route('/')
def index():
    return send_file('static/index.html')

@app.route('/api')
def api_info():
    return jsonify({
        "status": "running",
        "service": "Multi-GPU Video Generation API",
        "endpoints": {
            "generate": "POST /api/generate",
            "status": "GET /api/status/<task_id>",
            "download": "GET /api/download/<task_id>",
            "queue": "GET /api/queue"
        }
    })

@app.route('/api/generate', methods=['POST'])
def generate_video():
    """
    Generate video with voice cloning
    Input: video file + text
    """
    # Validate input
    video_file = request.files.get('video')
    
    if 'text' not in request.form:
        return jsonify({"error": "No text provided"}), 400
        
    text = request.form['text']
        
    # Generate task_id early so it's available for all paths
        
    # Generate task_id early so it's available for all paths
    task_id = f"task_{int(time.time())}"
    
    if video_file and video_file.filename != '' and allowed_video_file(video_file.filename):
        filename = secure_filename(video_file.filename)
        video_path = os.path.join(UPLOAD_FOLDER, f"{task_id}_{filename}")
        video_file.save(video_path)
        print(f"   ✅ Video Uploaded: {filename}")
    else:
        # Use default video
        if os.path.exists(DEFAULT_VIDEO_PATH):
            video_path = os.path.join(UPLOAD_FOLDER, f"{task_id}_default.mp4")
            subprocess.run(['cp', DEFAULT_VIDEO_PATH, video_path])
            print(f"   ⚠️ No video uploaded, using DEFAULT video")
        else:
            return jsonify({"error": "No video provided and default video missing"}), 400
    
    print(f"\n{'='*80}")
    print(f"📥 New Request: {task_id}")
    print(f"   Video: {os.path.basename(video_path)}")
    print(f"   Text: {text[:50]}...")
    print(f"{'='*80}\n")
    
    # Register initially
    scheduler.set_preprocessing_status(task_id, "Initializing...")
    
    # Start background processing
    thread = threading.Thread(target=process_task_background, args=(task_id, text, video_path))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "task_id": task_id,
        "message": "Task queued successfully",
        "queue_status": scheduler.get_gpu_status()
    })

def process_task_background(task_id, text, video_path):
    """Background task for audio extraction and TTS"""
    start_time = time.time()
    try:
        print(f"🔄 [Task {task_id}] Background processing started...")
        scheduler.set_preprocessing_status(task_id, "Extracting Audio...")
        
        # Update scheduler status to 'processing_audio' (Optional, scheduler keeps track)
        
        # Step 1: Extract audio from video
        print(f"🎵 [Task {task_id}] Extracting audio...")
        reference_audio = extract_audio_from_video(video_path)
        
        if not reference_audio:
            print(f"❌ [Task {task_id}] Audio extraction failed")
            return
        
        
        # Step 2: Generate voice-cloned audio
        print(f"🎤 [Task {task_id}] Generating voice clone...")
        scheduler.set_preprocessing_status(task_id, "Cloning Voice (This may take a few minutes)...")
        cloned_audio = generate_voice_cloning(text, reference_audio)
        
        if not cloned_audio:
            print(f"❌ [Task {task_id}] Voice cloning failed")
            return
            
        tts_duration = time.time() - start_time
        print(f"✅ [Task {task_id}] Voice cloned (took {tts_duration:.2f}s)")
        
        # Step 3: Add to GPU scheduler
        print(f"🎬 [Task {task_id}] Adding to GPU queue...")
        scheduler.clear_preprocessing_status(task_id) # Remove from pre-processing
        scheduler.add_task(
            video_path=video_path,
            audio_path=cloned_audio,
            text=text,
            task_id=task_id,
            tts_duration=tts_duration
        )
        
    except Exception as e:
        print(f"❌ [Task {task_id}] Background Process Error: {e}")
        scheduler.set_preprocessing_status(task_id, f"Error: {str(e)}")

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Get task status"""
    status = scheduler.get_task_status(task_id)
    gpu_status = scheduler.get_gpu_status()
    
    return jsonify({
        "task_id": task_id,
        "task_status": status,
        "gpu_status": gpu_status
    })

@app.route('/api/download/<task_id>', methods=['GET'])
def download_video(task_id):
    """Download generated video"""
    output_file = os.path.join(OUTPUT_FOLDER, f"output_{task_id}.mp4")
    
    if os.path.exists(output_file):
        return send_file(output_file, as_attachment=True)
    else:
        return jsonify({"error": "Video not ready or not found"}), 404

@app.route('/api/queue', methods=['GET'])
def get_queue_status():
    """Get overall queue and GPU status"""
    status = scheduler.get_gpu_status()
    
    # Add detailed queue list
    with scheduler.lock:
        queue_data = [
            {
                "task_id": t["task_id"],
                "status": "queued",
                "queued_at": t["queued_at"]
            } for t in scheduler.task_queue
        ]
        
        # Add active tasks too
        for t_id, t_data in scheduler.active_tasks.items():
            if t_data["status"] == "running":
                queue_data.insert(0, {
                    "task_id": t_id,
                    "status": "running",
                    "gpu_id": t_data["gpu_id"],
                    "start_time": t_data["start_time"]
                })

    status["queue"] = queue_data
    return jsonify(status)


@app.route('/api/admin/reset-gpus', methods=['POST'])
def reset_gpus():
    """
    Emergency GPU status reset
    Use when GPUs are stuck in 'busy' state
    """
    print("\n" + "="*80)
    print("🚨 ADMIN: Manual GPU Reset Triggered")
    print("="*80)
    
    with scheduler.lock:
        reset_count = 0
        # Free all GPUs
        for gpu_id in scheduler.gpu_config:
            if scheduler.gpu_config[gpu_id]["busy"]:
                print(f"   🟢 GPU {gpu_id}: busy → free")
                scheduler.gpu_config[gpu_id]["busy"] = False
                reset_count += 1
        
        # Mark stuck running tasks as failed
        failed_count = 0
        for task_id, task_data in scheduler.active_tasks.items():
            if task_data["status"] == "running":
                print(f"   ❌ Task {task_id}: running → failed (manual reset)")
                task_data["status"] = "failed"
                task_data["error"] = "Manual GPU reset"
                failed_count += 1
    
    # Trigger queue processing
    print(f"   ✅ Reset complete: {reset_count} GPUs freed, {failed_count} tasks failed")
    print(f"   🔄 Triggering queue processing...")
    print("="*80 + "\n")
    
    scheduler.process_next_in_queue()
    
    return jsonify({
        "success": True,
        "message": "All GPUs reset successfully",
        "gpus_freed": reset_count,
        "tasks_failed": failed_count,
        "queue_size": len(scheduler.task_queue),
        "gpu_status": scheduler.get_gpu_status()
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "gpus": scheduler.get_gpu_status()
    })


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 Multi-GPU Video Generation API Server")
    print("="*80)
    print("📍 Running on: http://0.0.0.0:5000")
    print("📊 GPU Status:")
    print("   - GPU 0: Port 8390")
    print("   - GPU 1: Port 8391")
    print("   - GPU 2: Port 8392")
    print("🎤 TTS Service: Port 18181 (New Container)")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
