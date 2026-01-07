#!/usr/bin/env python3
"""
Direct GPU Test Script
Tests GPU 1 and GPU 2 directly with default video
"""
import requests
import json
import subprocess
import os
import time

# Configuration
GPU_PORTS = {
    0: 8390,
    1: 8391,
    2: 8392
}

def prepare_test_files(gpu_id):
    """Copy default video and create dummy audio for testing"""
    gpu_data_dir = os.path.expanduser(f"~/heygem_data/gpu{gpu_id}/face2face/")
    os.makedirs(gpu_data_dir, exist_ok=True)
    
    # Default video path
    default_video = "/nvme0n1-disk/nvme01/HeyGem/webapp/default.mp4"
    
    if not os.path.exists(default_video):
        print(f"❌ Default video not found: {default_video}")
        return None, None
    
    # Copy video
    video_filename = f"test_gpu{gpu_id}_video.mp4"
    video_dest = os.path.join(gpu_data_dir, video_filename)
    subprocess.run(['cp', default_video, video_dest], check=True)
    
    # Create dummy audio (1 second of silence)
    audio_filename = f"test_gpu{gpu_id}_audio.wav"
    audio_dest = os.path.join(gpu_data_dir, audio_filename)
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-t', '5', '-q:a', '9', '-acodec', 'pcm_s16le', audio_dest
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    return video_filename, audio_filename

def submit_to_gpu(gpu_id, task_id, video_filename, audio_filename):
    """Submit task directly to GPU container"""
    port = GPU_PORTS[gpu_id]
    
    payload = {
        "audio_url": f"/code/data/face2face/{audio_filename}",
        "video_url": f"/code/data/face2face/{video_filename}",
        "code": task_id,
        "chaofen": 1,
        "watermark_switch": 0,
        "pn": 1
    }
    
    try:
        print(f"\n{'='*80}")
        print(f"📤 Submitting to GPU {gpu_id} (Port {port})")
        print(f"   Task ID: {task_id}")
        print(f"{'='*80}")
        
        response = requests.post(
            f"http://127.0.0.1:{port}/easy/submit",
            json=payload,
            timeout=30
        )
        
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print(f"✅ Task submitted successfully to GPU {gpu_id}")
            return True
        else:
            print(f"❌ Submission failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error submitting to GPU {gpu_id}: {e}")
        return False

def monitor_task(gpu_id, task_id, duration=30):
    """Monitor task status on GPU"""
    port = GPU_PORTS[gpu_id]
    print(f"\n🔍 Monitoring GPU {gpu_id} for {duration} seconds...")
    
    start = time.time()
    while time.time() - start < duration:
        try:
            response = requests.get(
                f"http://127.0.0.1:{port}/easy/query?code={task_id}",
                timeout=3
            )
            
            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                status = data.get('status', 0)
                progress = data.get('progress', 0)
                msg = data.get('msg', '')
                
                print(f"   [{int(time.time()-start)}s] Status: {status}, Progress: {progress}%, Msg: {msg}")
                
                if status == 2:  # Completed
                    print(f"✅ GPU {gpu_id} completed task!")
                    return True
                elif status == 3:  # Failed
                    print(f"❌ GPU {gpu_id} task failed: {msg}")
                    return False
        except Exception as e:
            print(f"   ⚠️  Query error: {e}")
        
        time.sleep(5)
    
    print(f"⏰ Monitoring timeout for GPU {gpu_id}")
    return None

def test_gpu(gpu_id):
    """Test a specific GPU"""
    print(f"\n{'#'*80}")
    print(f"# TESTING GPU {gpu_id}")
    print(f"{'#'*80}")
    
    task_id = f"test_direct_gpu{gpu_id}_{int(time.time())}"
    
    # Step 1: Prepare files
    print(f"\n1️⃣ Preparing test files for GPU {gpu_id}...")
    video_file, audio_file = prepare_test_files(gpu_id)
    
    if not video_file or not audio_file:
        print(f"❌ Failed to prepare files for GPU {gpu_id}")
        return False
    
    print(f"   Video: {video_file}")
    print(f"   Audio: {audio_file}")
    
    # Step 2: Submit task
    print(f"\n2️⃣ Submitting task to GPU {gpu_id}...")
    success = submit_to_gpu(gpu_id, task_id, video_file, audio_file)
    
    if not success:
        print(f"❌ Failed to submit task to GPU {gpu_id}")
        return False
    
    # Step 3: Monitor
    print(f"\n3️⃣ Monitoring GPU {gpu_id}...")
    result = monitor_task(gpu_id, task_id, duration=60)
    
    return result

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 DIRECT GPU TEST - GPU 1 & GPU 2")
    print("=" * 80)
    print("\nThis script tests GPU 1 and GPU 2 directly")
    print("to verify if they can process tasks.\n")
    
    # Test GPU 1
    print("\n" + "="*80)
    result_gpu1 = test_gpu(1)
    
    # Test GPU 2
    print("\n" + "="*80)
    result_gpu2 = test_gpu(2)
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"GPU 1: {'✅ PASSED' if result_gpu1 else '❌ FAILED' if result_gpu1 is False else '⏰ TIMEOUT'}")
    print(f"GPU 2: {'✅ PASSED' if result_gpu2 else '❌ FAILED' if result_gpu2 is False else '⏰ TIMEOUT'}")
    print("="*80)
    
    print("\n💡 TIP: Run 'nvidia-smi' in another terminal while this script runs")
    print("   to see if GPU 1 and GPU 2 memory usage increases.\n")
