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

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = '/nvme0n1-disk/HeyGem/webapp/uploads'
OUTPUT_FOLDER = '/nvme0n1-disk/HeyGem/webapp/outputs'
TEMP_FOLDER = '/nvme0n1-disk/HeyGem/webapp/temp'
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
        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le', '-ar', '44100',
            audio_output, '-y'
        ], check=True, capture_output=True)
        
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
    tts_ref_dir = os.path.expanduser("~/heygem_data/voice/data/reference")
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
            timeout=240  # Longer timeout for voice cloning
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
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    if 'text' not in request.form:
        return jsonify({"error": "No text provided"}), 400
    
    video_file = request.files['video']
    text = request.form['text']
    
    if video_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not allowed_video_file(video_file.filename):
        return jsonify({"error": "Invalid video format"}), 400
    
    # Save uploaded video
    filename = secure_filename(video_file.filename)
    task_id = f"task_{int(time.time())}"
    video_path = os.path.join(UPLOAD_FOLDER, f"{task_id}_{filename}")
    video_file.save(video_path)
    
    print(f"\n{'='*80}")
    print(f"📥 New Request: {task_id}")
    print(f"   Video: {filename}")
    print(f"   Text: {text[:50]}...")
    print(f"{'='*80}\n")
    
    # Step 1: Extract audio from video
    print(f"🎵 Extracting audio from video...")
    reference_audio = extract_audio_from_video(video_path)
    
    if not reference_audio:
        return jsonify({"error": "Audio extraction failed"}), 500
    
    print(f"✅ Audio extracted: {reference_audio}")
    
    # Step 2: Generate voice-cloned audio
    print(f"🎤 Generating voice clone...")
    cloned_audio = generate_voice_cloning(text, reference_audio)
    
    if not cloned_audio:
        return jsonify({"error": "Voice cloning failed"}), 500
    
    print(f"✅ Voice cloned: {cloned_audio}")
    
    # Step 3: Add to GPU scheduler
    print(f"🎬 Adding to GPU queue...")
    scheduler.add_task(
        video_path=video_path,
        audio_path=cloned_audio,
        text=text,
        task_id=task_id
    )
    
    return jsonify({
        "success": True,
        "task_id": task_id,
        "message": "Video generation started",
        "queue_status": scheduler.get_gpu_status()
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
def get_queue_status():
    """Get overall queue and GPU status"""
    return jsonify(scheduler.get_gpu_status())

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
