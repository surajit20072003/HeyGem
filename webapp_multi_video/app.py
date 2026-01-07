#!/usr/bin/env python3
"""
Flask API Server for Multi-Video Random Merge Processing
Accepts multiple videos, randomly merges them per chunk
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import subprocess
import time
from werkzeug.utils import secure_filename
from multi_video_scheduler import scheduler

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
INPUT_VIDEOS_FOLDER = os.path.join(BASE_DIR, 'input_videos')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
TEMP_FOLDER = os.path.join(BASE_DIR, 'temp')
TTS_API = 'http://localhost:18181'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INPUT_VIDEOS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wav', 'mp3'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_voice_cloning(text: str, reference_audio: str) -> str:
    """Generate voice-cloned audio using TTS"""
    import requests
    
    text = ' '.join(text.split())
    
    if not text or len(text.strip()) == 0:
        print(f"   ❌ Empty text, using reference audio")
        return reference_audio
    
    print(f"   📝 TTS Request: '{text[:80]}...' ({len(text)} chars)")
    
    # Copy to TTS directory
    tts_ref_dir = os.path.expanduser("~/heygem_data/tts/reference")
    os.makedirs(tts_ref_dir, exist_ok=True)
    
    ref_filename = os.path.basename(reference_audio)
    tts_ref_path = os.path.join(tts_ref_dir, ref_filename)
    subprocess.run(['cp', reference_audio, tts_ref_path])
    
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
            timeout=240
        )
        
        print(f"   Status: {response.status_code}, Size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            output_audio = os.path.join(TEMP_FOLDER, f"cloned_audio_{int(time.time())}.wav")
            with open(output_audio, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(output_audio)
            if file_size < 10000:
                print(f"   ⚠️  Audio too small, using reference")
                return reference_audio
            
            print(f"   ✅ Generated audio: {file_size} bytes")
            return output_audio
        else:
            print(f"   ❌ TTS error: {response.status_code}")
            return reference_audio
            
    except Exception as e:
        print(f"   ❌ TTS error: {e}")
        return reference_audio


@app.route('/')
def index():
    return send_file('static/index.html')


@app.route('/api')
def api_info():
    return jsonify({
        "status": "running",
        "service": "Multi-Video Random Merge API",
        "mode": "3 GPUs Parallel (Random Video Merge)",
        "endpoints": {
            "generate": "POST /api/generate",
            "status": "GET /api/status/<task_id>",
            "download": "GET /api/download/<task_id>",
            "gpu_status": "GET /api/gpu-status"
        }
    })


@app.route('/api/generate', methods=['POST'])
def generate_video():
    """
    Generate video with multi-video random merging
    Input: multiple video files + reference audio + text
    """
    # Validate inputs
    if 'videos' not in request.files:
        return jsonify({"error": "No video files provided"}), 400
    
    if 'reference_audio' not in request.files:
        return jsonify({"error": "No reference audio provided"}), 400
    
    if 'text' not in request.form:
        return jsonify({"error": "No text provided"}), 400
    
    video_files = request.files.getlist('videos')
    reference_audio_file = request.files['reference_audio']
    text = request.form['text']
    
    if len(video_files) == 0:
        return jsonify({"error": "No videos selected"}), 400
    
    # Save task ID
    task_id = f"multi_{int(time.time())}"
    
    print(f"\n{'='*80}")
    print(f"📥 New Multi-Video Request: {task_id}")
    print(f"   Videos: {len(video_files)} files")
    print(f"   Text: {text[:50]}...")
    print(f"   Mode: Random Video Merge (3 GPUs)")
    print(f"{'='*80}\n")
    
    # Save all input videos
    input_video_paths = []
    for i, video_file in enumerate(video_files):
        if video_file and allowed_file(video_file.filename):
            filename = secure_filename(video_file.filename)
            video_path = os.path.join(INPUT_VIDEOS_FOLDER, f"{task_id}_input{i+1}_{filename}")
            video_file.save(video_path)
            input_video_paths.append(video_path)
            print(f"   ✅ Saved: {filename}")
    
    if len(input_video_paths) == 0:
        return jsonify({"error": "No valid videos uploaded"}), 400
    
    # Save reference audio
    ref_audio_path = os.path.join(TEMP_FOLDER, f"ref_audio_{task_id}.wav")
    reference_audio_file.save(ref_audio_path)
    print(f"   ✅ Reference audio saved")
    
    # Generate voice clone
    print(f"🎤 Generating voice clone...")
    tts_start_time = time.time()
    cloned_audio = generate_voice_cloning(text, ref_audio_path)
    tts_duration = time.time() - tts_start_time
    
    if not cloned_audio:
        return jsonify({"error": "Voice cloning failed"}), 500
    
    print(f"✅ Voice cloned: {cloned_audio} (took {tts_duration:.2f}s)")
    
    # Start multi-video processing
    print(f"🎬 Starting multi-video processing...")
    scheduler.add_task(
        input_videos=input_video_paths,
        audio_path=cloned_audio,
        task_id=task_id
    )
    
    return jsonify({
        "success": True,
        "task_id": task_id,
        "message": "Multi-video generation started (Random merge mode)",
        "mode": "multi_video_random",
        "input_videos": len(input_video_paths),
        "tts_duration": round(tts_duration, 2),
        "gpu_status": scheduler.get_gpu_status()
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


@app.route('/api/gpu-status', methods=['GET'])
def get_gpu_status():
    """Get GPU status"""
    return jsonify(scheduler.get_gpu_status())


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "mode": "multi_video_random",
        "gpus": scheduler.get_gpu_status()
    })


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 Multi-Video Random Merge API Server")
    print("="*80)
    print("📍 Running on: http://0.0.0.0:5002")
    print("🎬 Processing Mode: Random Video Merge (3 GPUs)")
    print("📊 GPU Configuration:")
    print("   - GPU 0: Port 8390 (Chunk 1 - Random merge)")
    print("   - GPU 1: Port 8391 (Chunk 2 - Random merge)")
    print("   - GPU 2: Port 8392 (Chunk 3 - Random merge)")
    print("🎤 TTS Service: Port 18181")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)
