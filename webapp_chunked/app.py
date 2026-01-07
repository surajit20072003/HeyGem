#!/usr/bin/env python3
"""
Flask API Server for Chunked Multi-GPU Video Generation
Splits audio into chunks, processes in parallel, then merges
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import subprocess
import time
import threading
from werkzeug.utils import secure_filename
from chunked_scheduler import scheduler
from text_normalization import latex_to_speech

app = Flask(__name__)
CORS(app)

# Configuration
# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
TEMP_FOLDER = os.path.join(BASE_DIR, 'temp')
TTS_API = 'http://localhost:18181'  # Fish-Speech container

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
        cmd = ['/usr/bin/ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', '-t', '15', audio_output]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return audio_output
    except Exception as e:
        print(f"❌ Audio extraction error: {e}")
        return None


def generate_voice_cloning(text: str, reference_audio: str) -> str:
    """Generate voice-cloned audio using TTS"""
    import requests
    
    # Clean text
    # Clean text
    text = ' '.join(text.split())
    
    # Normalize Math/LaTeX if present
    print(f"   📐 Normalizing Text (Before): {text[:50]}...")
    text = latex_to_speech(text)
    print(f"   📐 Normalizing Text (After):  {text[:50]}...")
    
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
            timeout=6000 # Increased timeout
        )
        
        print(f"   Status: {response.status_code}, Size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            output_audio = os.path.join(TEMP_FOLDER, f"cloned_audio_{int(time.time())}.wav")
            with open(output_audio, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(output_audio)
            if file_size < 10000:
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
        "service": "Chunked Multi-GPU Video Generation API",
        "mode": "3 GPUs Parallel (Audio Chunking)",
        "endpoints": {
            "generate": "POST /api/generate",
            "status": "GET /api/status/<task_id>",
            "download": "GET /api/download/<task_id>",
            "gpu_status": "GET /api/gpu-status"
        }
    })


def process_task_background(task_id, text, video_path):
    """Background task for audio extraction, TTS, and scheduling"""
    
    start_time = time.time()
    try:
        scheduler.set_preprocessing_status(task_id, "Extracting Audio...")
        print(f"🔄 [Task {task_id}] Background processing started...")
        
        # Step 1: Extract audio from video
        print(f"🎵 [Task {task_id}] Extracting audio using ffmpeg...")
        reference_audio = extract_audio_from_video(video_path)
        
        if not reference_audio:
            print(f"❌ [Task {task_id}] Audio extraction failed")
            scheduler.set_preprocessing_status(task_id, "Error: Audio extraction failed")
            return
            
        print(f"✅ [Task {task_id}] Audio extracted")

        # Step 2: Generate voice-cloned audio
        print(f"🎤 [Task {task_id}] Generating voice clone...")
        scheduler.set_preprocessing_status(task_id, "Cloning Voice (This may take a few minutes)...")
        cloned_audio = generate_voice_cloning(text, reference_audio)
        
        if not cloned_audio:
            print(f"❌ [Task {task_id}] Voice cloning failed")
            scheduler.set_preprocessing_status(task_id, "Error: Voice cloning failed")
            return
            
        tts_duration = time.time() - start_time
        print(f"✅ [Task {task_id}] Voice cloned (took {tts_duration:.2f}s)")
        
        # Step 3: Add to chunked scheduler
        print(f"🎬 [Task {task_id}] Adding to Chunked Scheduler...")
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


@app.route('/api/generate', methods=['POST'])
def generate_video():
    """
    Generate video with chunked parallel processing (Async)
    Input: video file (optional) + text
    Output: task_id immediately
    """
    
    # Generate task_id early
    task_id = f"chunked_{int(time.time())}"
    
    if 'text' not in request.form:
        return jsonify({"error": "No text provided"}), 400
        
    text = request.form['text']
    
    # Handle video file (optional)
    video_file = request.files.get('video')
    
    if video_file and video_file.filename != '':
        # User uploaded video
        if not allowed_video_file(video_file.filename):
            return jsonify({"error": "Invalid video format"}), 400
            
        filename = secure_filename(video_file.filename)
        video_path = os.path.join(UPLOAD_FOLDER, f"{task_id}_{filename}")
        video_file.save(video_path)
    else:
        # Use default video
        print("ℹ️ No video uploaded, using default")
        default_video_path = os.path.join(BASE_DIR, "default.mp4")
        if not os.path.exists(default_video_path):
             return jsonify({"error": "Default video not found on server"}), 500
             
        # Copy default video to uploads with task_id to avoid conflicts/overwrites
        filename = "default.mp4"
        video_path = os.path.join(UPLOAD_FOLDER, f"{task_id}_default.mp4")
        subprocess.run(['cp', default_video_path, video_path])

    print(f"\n{'='*80}")
    print(f"📥 New Chunked Request: {task_id}")
    print(f"   Video: {filename}")
    print(f"   Text: {text[:50]}...")
    print(f"   Mode: 3 GPU Parallel Chunking (Async)")
    print(f"{'='*80}\n")
    
    # Register initially
    scheduler.set_preprocessing_status(task_id, "Initializing...")
    
    # Start background thread
    thread = threading.Thread(target=process_task_background, args=(task_id, text, video_path))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "task_id": task_id,
        "message": "Task queued successfully",
        "mode": "chunked_parallel_async"
    })


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
def get_queue():
    """Get current task queue status"""
    with scheduler.lock:
        queue_data = [
            {
                "task_id": t,
                "status": scheduler.active_tasks[t]["status"],
                "queued_at": scheduler.active_tasks[t].get("start_time", 0)
            } for t in scheduler.active_tasks if scheduler.active_tasks[t]["status"] in ["queued", "splitting", "processing", "merging"]
        ]
        return jsonify({
            "queue_size": len(queue_data),
            "queue": queue_data
        })

@app.route('/api/gpu-status', methods=['GET'])
def get_gpu_status():
    """Get GPU status"""
    return jsonify(scheduler.get_gpu_status())


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "mode": "chunked_parallel",
        "gpus": scheduler.get_gpu_status()
    })


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 Chunked Multi-GPU Video Generation API Server")
    print("="*80)
    print("📍 Running on: http://0.0.0.0:5001")
    print("🎬 Processing Mode: 3 GPU Parallel (Audio Chunking)")
    print("📊 GPU Configuration:")
    print("   - GPU 0: Port 8390 (Chunk 1)")
    print("   - GPU 1: Port 8391 (Chunk 2)")
    print("   - GPU 2: Port 8392 (Chunk 3)")
    print("🎤 TTS Service: Port 18181")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
