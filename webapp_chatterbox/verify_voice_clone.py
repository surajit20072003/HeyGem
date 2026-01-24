#!/usr/bin/env python3
import requests
import os
import time
import subprocess
from datetime import datetime

# Configuration
WEBAPP_URL = "http://localhost:5003"
TTS_PORTS = [18182, 18183]
GPU_PORTS = [8390, 8391]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REFERENCE_AUDIO = os.path.join(BASE_DIR, 'reference_audio.wav')
TEST_TEXT = "Hello! This is a test to verify if the voice cloning system is working correctly on this GPU."

def check_connectivity():
    print(f"\n--- 🌐 Connectivity Check ({datetime.now().strftime('%H:%M:%S')}) ---")
    
    # Check Webapp
    try:
        res = requests.get(f"{WEBAPP_URL}/api/info", timeout=2)
        print(f"✅ Webapp (5003): ONLINE")
    except:
        print(f"❌ Webapp (5003): OFFLINE (Run 'python3 app.py' in webapp_dual_tts)")

    # Check TTS
    for port in TTS_PORTS:
        try:
            res = requests.get(f"http://localhost:{port}/", timeout=2)
            print(f"✅ TTS Container (Port {port}): ONLINE")
        except:
            print(f"❌ TTS Container (Port {port}): OFFLINE")

    # Check GPU
    for port in GPU_PORTS:
        try:
            res = requests.get(f"http://localhost:{port}/easy/query?code=test", timeout=2)
            print(f"✅ GPU Container (Port {port}): ONLINE")
        except:
            print(f"❌ GPU Container (Port {port}): OFFLINE")

def test_voice_clone(port):
    print(f"\n--- 🎤 Testing Voice Clone on Port {port} ---")
    
    # 1. Prepare reference audio in the shared volume
    tts_id = 0 if port == 18182 else 1
    tts_ref_dir = os.path.expanduser(f"~/heygem_data/tts{tts_id}/reference")
    os.makedirs(tts_ref_dir, exist_ok=True)
    
    ref_basename = os.path.basename(REFERENCE_AUDIO)
    target_ref_path = os.path.join(tts_ref_dir, f"test_{ref_basename}")
    
    if not os.path.exists(REFERENCE_AUDIO):
        print(f"❌ Reference audio missing at {REFERENCE_AUDIO}")
        return False
        
    subprocess.run(['cp', REFERENCE_AUDIO, target_ref_path])
    print(f"   ✓ Copied reference audio to shared volume")

    # 2. Call TTS API
    payload = {
        "text": TEST_TEXT,
        "reference_audio": f"/code/data/reference/test_{ref_basename}",
        "reference_text": "",
        "format": "wav"
    }
    
    try:
        start_time = time.time()
        print(f"   🚀 Sending TTS request...")
        response = requests.post(
            f"http://localhost:{port}/v1/invoke",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            duration = time.time() - start_time
            size = len(response.content)
            print(f"   ✅ SUCCESS! Received {size} bytes in {duration:.2f}s")
            
            # Save for manual verification
            output_file = f"test_output_tts_{port}.wav"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"   💾 Saved test output to: {output_file}")
            return True
        else:
            print(f"   ❌ FAILED! Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_gpu_assignment():
    print(f"\n--- 📋 Testing GPU Assignment Logic ---")
    try:
        res = requests.get(f"{WEBAPP_URL}/api/queue", timeout=5)
        if res.status_code == 200:
            data = res.json()
            gpus = data.get('gpus', {})
            print(f"   📊 Current GPU Status:")
            for gpu_id, info in gpus.items():
                status = "BUSY 🔴" if info.get('busy') else "FREE 🟢"
                task = info.get('current_task') or 'None'
                print(f"      GPU {gpu_id}: {status} (Task: {task}, Port: {info.get('video_port')})")
            
            # Find which would be picked next
            free_gpus = [gid for gid, info in gpus.items() if not info.get('busy')]
            if free_gpus:
                print(f"   🎯 Next available GPU will be: GPU {free_gpus[0]}")
            else:
                print(f"   ⚠️ Both GPUs are currently busy.")
        else:
            print(f"   ❌ Could not get queue status from webapp")
    except Exception as e:
        print(f"   ❌ Error checking assignment: {e}")

if __name__ == "__main__":
    print("="*80)
    print("🔍 HeyGem Dual Setup - Comprehensive Verification")
    print("="*80)
    
    check_connectivity()
    
    # Test TTS 0
    test_voice_clone(18182)
    
    # Test TTS 1
    test_voice_clone(18183)
    
    # Check GPU status
    test_gpu_assignment()
    
    print("\n" + "="*80)
    print("🏁 Verification Complete")
    print("="*80)
