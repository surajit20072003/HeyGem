#!/usr/bin/env python3
"""
Chatterbox TTS Service
Provides a Fish-Speech-compatible API interface using Chatterbox-Turbo
Supports voice cloning with reference audio
"""
import os
import sys
import argparse
import io
import torch
import torchaudio as ta
from flask import Flask, request, jsonify, send_file
from datetime import datetime
import subprocess

# Import Chatterbox
try:
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    CHATTERBOX_AVAILABLE = True
except ImportError:
    CHATTERBOX_AVAILABLE = False
    print("❌ Chatterbox not installed. Run: pip install chatterbox-tts")
    sys.exit(1)

app = Flask(__name__)

# Global model instance
model = None
gpu_id = None
port = None

def load_model(device="cuda"):
    """Load Chatterbox-Turbo model"""
    global model
    
    print(f"\n🔄 Loading Chatterbox-Turbo on {device}...")
    start_time = datetime.now()
    
    try:
        model = ChatterboxTurboTTS.from_pretrained(device=device)
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"✅ Model loaded successfully in {elapsed:.2f}s")
        print(f"   Sample Rate: {model.sr} Hz")
        return True
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return False

@app.route('/', methods=['GET'])
def index():
    """Health check endpoint"""
    return jsonify({
        "service": "Chatterbox TTS Service",
        "status": "online",
        "model": "Chatterbox-Turbo",
        "gpu": gpu_id,
        "port": port,
        "sample_rate": model.sr if model else None
    })

import gc

# ... (imports)

def chunk_text(text, max_chars=300):
    """
    Split text into chunks of maximum max_chars, generally respecting sentence boundaries.
    """
    text = text.strip()
    if not text:
        return []
        
    chunks = []
    current_chunk = ""
    
    # Split by common sentence terminators
    # This is a simple splitter; for production, NLTK or similar is better
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
            
            # If a single sentence is too long, force split it
            while len(current_chunk) > max_chars:
                # Find a suitable break point (comma, space)
                break_point = current_chunk.rfind(',', 0, max_chars)
                if break_point == -1:
                    break_point = current_chunk.rfind(' ', 0, max_chars)
                
                if break_point != -1:
                    chunks.append(current_chunk[:break_point+1].strip())
                    current_chunk = current_chunk[break_point+1:]
                else:
                    # Hard chop if no spaces (rare)
                    chunks.append(current_chunk[:max_chars])
                    current_chunk = current_chunk[max_chars:]
    
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

@app.route('/v1/unload', methods=['POST'])
def unload():
    """Unload model to free GPU memory"""
    global model
    
    if model is None:
        return jsonify({"status": "already_unloaded"})
    
    try:
        print(f"\n🧹 [GPU {gpu_id}] Unloading model...")
        del model
        model = None
        gc.collect()
        torch.cuda.empty_cache()
        
        # Verify memory cleared
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            free_mem, total_mem = torch.cuda.mem_get_info(gpu_id)
            print(f"   ✅ Model unloaded. Free VRAM: {free_mem/1024**3:.2f} GB / {total_mem/1024**3:.2f} GB")
            
        return jsonify({"status": "unloaded"})
    except Exception as e:
        print(f"❌ Error unloading model: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/v1/invoke', methods=['POST'])
def invoke():
    """
    TTS generation endpoint (Fish-Speech compatible)
    """
    global model
    
    # Auto-load model if not loaded
    if model is None:
        print(f"\n🔄 Auto-loading model for request...")
        device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
        if not load_model(device):
            return jsonify({"error": "Failed to load model"}), 500
    
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get('text', '')
        reference_audio = data.get('reference_audio')
        audio_format = data.get('format', 'wav')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # CHUNKING LOGIC
        chunks = chunk_text(text, max_chars=300)
        print(f"\n🎤 [GPU {gpu_id}] TTS Request (Chunked strategy):")
        print(f"   Total Text Length: {len(text)} chars")
        print(f"   Chunk Count: {len(chunks)}")
        print(f"   Reference: {reference_audio if reference_audio else 'None (default voice)'}")
        
        start_time = datetime.now()
        generated_tensors = []
        
        for i, chunk in enumerate(chunks):
            print(f"   Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
            
            # Generate audio for chunk
            if reference_audio and os.path.exists(reference_audio):
                wav_chunk = model.generate(chunk, audio_prompt_path=reference_audio)
            else:
                wav_chunk = model.generate(chunk)
            
            # Ensure it's 2D (1, T) or 1D (T) -> make it list
            if isinstance(wav_chunk, torch.Tensor):
                if wav_chunk.dim() == 1:
                    wav_chunk = wav_chunk.unsqueeze(0)
                generated_tensors.append(wav_chunk.cpu())
            
            # Optional: Add small silence between chunks?
            # silence = torch.zeros(1, int(model.sr * 0.2)) # 200ms silence
            # generated_tensors.append(silence)
        
        if not generated_tensors:
             return jsonify({"error": "No audio generated"}), 500

        # Concatenate all chunks
        full_wav = torch.cat(generated_tensors, dim=1)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Convert to bytes
        audio_buffer = io.BytesIO()
        ta.save(audio_buffer, full_wav, model.sr, format=audio_format)
        audio_buffer.seek(0)
        
        # Audio Speed Adjustment (default 0.8)
        speed = float(data.get('speed', 0.8))
        
        if speed != 1.0:
            try:
                print(f"   ⏱️  Adjusting speed to {speed}x using ffmpeg...")
                
                # Use ffmpeg via subprocess to change tempo (atempo filter)
                cmd = [
                    'ffmpeg', '-y',
                    '-f', audio_format, '-i', 'pipe:0',  # Input from stdin
                    '-filter:a', f'atempo={speed}',      # Tempo filter
                    '-f', audio_format, 'pipe:1'         # Output to stdout
                ]
                
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Pass original audio to ffmpeg stdin and get result from stdout
                out_data, err_data = process.communicate(input=audio_buffer.getvalue())
                
                if process.returncode != 0:
                    print(f"   ⚠️  ffmpeg speed adjustment failed: {err_data.decode()}")
                    audio_buffer.seek(0) # Revert to original on failure
                else:
                    audio_buffer = io.BytesIO(out_data)
                    print(f"   ✅ Speed adjusted successfully")
                    
            except Exception as e:
                print(f"   ⚠️  Speed adjustment error: {e}")
                audio_buffer.seek(0)
        
        audio_size = len(audio_buffer.getvalue())
        print(f"   ✅ Generated {audio_size/1024:.1f} KB in {elapsed:.2f}s")
        
        return send_file(
            audio_buffer,
            mimetype=f'audio/{audio_format}',
            as_attachment=False,
            download_name=f'output.{audio_format}'
        )
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        # Always unload model after request to free VRAM for other workloads
        if model is not None:
            print(f"\n🧹 [GPU {gpu_id}] Auto-unloading model to free VRAM...")
            del model
            model = None
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            print(f"   ✅ VRAM released")

@app.route('/health', methods=['GET'])
def health():
    """Health check for monitoring"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "gpu": gpu_id
    })

def main():
    global gpu_id, port
    
    parser = argparse.ArgumentParser(description='Chatterbox TTS Service')
    parser.add_argument('--port', type=int, default=20182, help='Port to run on (default: 20182)')
    parser.add_argument('--gpu', type=int, default=0, help='GPU ID to use (default: 0)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    
    args = parser.parse_args()
    
    gpu_id = args.gpu
    port = args.port
    
    # Set CUDA device
    if torch.cuda.is_available():
        torch.cuda.set_device(gpu_id)
        device = f"cuda:{gpu_id}"
        print(f"🎮 Using GPU {gpu_id}")
    else:
        device = "cpu"
        print("⚠️  CUDA not available, using CPU")
    
    # Model loaded lazily per request — server starts with 0 VRAM usage
    print(f"⚡ Lazy load mode: model will load on first /v1/invoke request")
    
    # Start Flask server
    print(f"\n🚀 Starting Chatterbox TTS Service")
    print(f"   Port: {port}")
    print(f"   GPU: {gpu_id}")
    print(f"   Endpoint: http://localhost:{port}/v1/invoke")
    print("=" * 80)
    
    app.run(
        host=args.host,
        port=port,
        debug=False,
        threaded=True
    )

if __name__ == '__main__':
    main()
