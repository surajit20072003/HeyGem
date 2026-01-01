#!/usr/bin/env python3
"""
Enhanced HeyGem Task Monitor with Percentage Progress
Shows real-time progress based on file generation count
"""
import time
import os
import subprocess
from datetime import datetime

# Configuration
TASK_CODE = "perf_test_1766650156"
TEMP_DIR = f"/root/heygem_data/gpu0/temp/{TASK_CODE}"
OUTPUT_PATH = f"/root/heygem_data/gpu0/temp/{TASK_CODE}-r.mp4"
CHECK_INTERVAL = 5  # seconds
MAX_WAIT = 1800  # 30 minutes

# Estimate total frames based on audio/video length
# Adjust this based on your video length (frames = duration * fps)
ESTIMATED_TOTAL_FRAMES = 10000  # Will auto-adjust based on first reading

def get_gpu_stats():
    """Get GPU utilization and memory"""
    try:
        result = subprocess.run([
            'nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, check=True)
        
        for line in result.stdout.strip().split('\n'):
            parts = [x.strip() for x in line.split(',')]
            if parts[0] == '0':
                return int(parts[1]), int(parts[2])  # util%, memory MB
    except:
        pass
    return 0, 0

def count_generated_files():
    """Count AVI and PNG files in temp directory"""
    avi_count = 0
    png_count = 0
    
    try:
        # Count AVI files
        avi_dir = os.path.join(TEMP_DIR, 'avi')
        if os.path.exists(avi_dir):
            avi_count = len([f for f in os.listdir(avi_dir) if f.endswith('.avi')])
        
        # Count PNG files  
        png_dir = os.path.join(TEMP_DIR, 'png')
        if os.path.exists(png_dir):
            png_count = len([f for f in os.listdir(png_dir) if f.endswith('.png')])
    except:
        pass
    
    return avi_count, png_count

def format_time(seconds):
    """Format seconds to MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def create_progress_bar(percentage, width=40):
    """Create visual progress bar"""
    filled = int(width * percentage / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}]"

# Main monitoring loop
print("=" * 80)
print("🎬 HeyGem Video Generation Monitor - Real-time Progress")
print("=" * 80)
print(f"Task Code: {TASK_CODE}")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

start_time = time.time()
elapsed = 0
last_avi_count = 0
last_png_count = 0
actual_total_frames = ESTIMATED_TOTAL_FRAMES

print("\n⏳ Monitoring (Ctrl+C to stop)...\n")

try:
    while elapsed < MAX_WAIT:
        # Check if output file exists (100% complete)
        if os.path.exists(OUTPUT_PATH):
            # Wait 5 seconds to ensure file write is complete
            print("\n⏳ Video file detected! Waiting 5s to ensure complete write...")
            time.sleep(5)
            
            # Verify file size stability
            size1 = os.path.getsize(OUTPUT_PATH)
            time.sleep(2)
            size2 = os.path.getsize(OUTPUT_PATH)
            
            if size1 != size2:
                print("⚠️  File still being written, waiting 10 more seconds...")
                time.sleep(10)
            
            file_size = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)  # MB
            
            print("\n" + "=" * 80)
            print("✅ VIDEO GENERATION COMPLETE!")
            print("=" * 80)
            print(f"📁 Location: {OUTPUT_PATH}")
            print(f"📊 Size: {file_size:.1f} MB")
            print(f"⏱️  Total time: {format_time(elapsed)}")
            print("=" * 80)
            
            # Copy to main directory with verification
            output_name = f"output_{TASK_CODE}.mp4"
            print(f"📋 Copying complete file...")
            subprocess.run([
                'cp', OUTPUT_PATH,
                f"/nvme0n1-disk/HeyGem/{output_name}"
            ], capture_output=True)
            
            # Verify copy
            copied_size = os.path.getsize(f"/nvme0n1-disk/HeyGem/{output_name}") / (1024 * 1024)
            if abs(copied_size - file_size) < 0.1:  # Within 0.1 MB
                print(f"✅ Copied successfully: /nvme0n1-disk/HeyGem/{output_name} ({copied_size:.1f} MB)")
            else:
                print(f"⚠️  Copy size mismatch! Original: {file_size:.1f} MB, Copied: {copied_size:.1f} MB")
            print("=" * 80)
            break
        
        # Get current stats
        gpu_util, gpu_mem = get_gpu_stats()
        avi_count, png_count = count_generated_files()
        
        # Auto-adjust total estimate based on growth
        if avi_count > last_avi_count and elapsed > 60:
            # Estimate based on rate: frames_per_second * remaining_time
            rate = avi_count / elapsed if elapsed > 0 else 0
            if rate > 0:
                actual_total_frames = max(actual_total_frames, int(avi_count * 1.2))
        
        # Calculate progress percentage (based on AVI files primarily)
        if avi_count > 0:
            progress = min(95, int((avi_count / actual_total_frames) * 100))
        else:
            progress = 0
        
        # Create progress bar
        progress_bar = create_progress_bar(progress)
        
        # Print single-line status with percentage
        print(f"\r🎥 {progress_bar} {progress:3d}%  |  "
              f"⏱️  {format_time(elapsed)}  |  "
              f"GPU: {gpu_util:3d}% / {gpu_mem/1024:.1f}GB  |  "
              f"Files: {avi_count:,} AVI, {png_count:,} PNG  "
              , end='', flush=True)
        
        # New line when significant progress made
        if avi_count > last_avi_count + 100:
            print()  # New line for readability
            last_avi_count = avi_count
        
        last_png_count = png_count
        time.sleep(CHECK_INTERVAL)
        elapsed = time.time() - start_time

    if elapsed >= MAX_WAIT:
        print(f"\n\n⏰ Max wait time ({MAX_WAIT/60:.0f} min) reached")
        print("   Task may still be processing in background")

except KeyboardInterrupt:
    print("\n\n⚠️  Monitoring stopped by user")
    print(f"   Elapsed: {format_time(elapsed)}")
    print("   Task continues in background")

print("\n🏁 Monitor completed!")
print("=" * 80)
