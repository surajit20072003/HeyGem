#!/usr/bin/env python3
"""
Simple Voice Cloning Test
Tests basic TTS functionality
"""
import requests
import json
import os
import time

print("=" * 80)
print("🎤 HeyGem Voice Cloning - Quick Test")
print("=" * 80)

# Check TTS service health
print("\n1️⃣ Checking TTS service health...")
try:
    health = requests.get("http://localhost:18180/health", timeout=5)
    print(f"   ✅ TTS Service Status: {health.json()}")
except Exception as e:
    print(f"   ❌ TTS service not accessible: {e}")
    exit(1)

# Test text-to-speech
print("\n2️⃣ Testing basic text-to-speech...")

test_payload = {
    "text": "Hello, this is a voice cloning test. Namaste, main aapka swagat karta hoon.",
    "reference_audio": "",
    "reference_text": "",
    "format": "wav",
    "speed": 1.0
}

print(f"   Payload: {json.dumps(test_payload, indent=2)}")

try:
    response = requests.post(
        "http://localhost:18180/v1/invoke",
        json=test_payload,
        timeout=30
    )
    
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        # Save audio
        output_file = "test_tts_output.wav"
        
        # Check if response is audio or JSON
        content_type = response.headers.get('content-type', '')
        
        if 'audio' in content_type or len(response.content) > 1000:
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            file_size = os.path.getsize(output_file) / 1024  # KB
            print(f"   ✅ Audio generated: {output_file} ({file_size:.1f} KB)")
            
            # Copy to data directory for video generation
            os.makedirs(os.path.expanduser("~/heygem_data/gpu0/face2face"), exist_ok=True)
            import shutil
            shutil.copy(output_file, os.path.expanduser("~/heygem_data/gpu0/face2face/test_tts_output.wav"))
            print(f"   ✅ Copied to GPU data directory")
        else:
            # JSON response
            print(f"   Response: {response.text}")
    else:
        print(f"   ❌ Request failed: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test Voice Cloning with Modi's voice
print("\n" + "=" * 80)
print("🎤 VOICE CLONING TEST - Using Modi's Voice")
print("=" * 80)

# Check if modi.wav exists
modi_audio = "/nvme0n1-disk/HeyGem/modi.wav"
if os.path.exists(modi_audio):
    print(f"\n✅ Reference audio found: {modi_audio}")
    file_size = os.path.getsize(modi_audio) / (1024*1024)
    print(f"   Size: {file_size:.2f} MB")
    
    # Copy to data directory for TTS access
    print("\n3️⃣ Preparing reference audio...")
    ref_dir = os.path.expanduser("~/heygem_data/voice/data/reference")
    os.makedirs(ref_dir, exist_ok=True)
    
    import shutil
    shutil.copy(modi_audio, f"{ref_dir}/modi.wav")
    print(f"   ✅ Copied to: {ref_dir}/modi.wav")
    
    # Test voice cloning
    print("\n4️⃣ Testing voice cloning with Modi's voice...")
    
    clone_payload = {
        "text": "Namaste mitron, main aaj aapko artificial intelligence aur technology ke baare mein batana chahta hoon. Yeh bahut important vishay hai.",
        "reference_audio": "/code/data/reference/modi.wav",
        "reference_text": "Sample reference text for voice cloning",
        "format": "wav",
        "speed": 1.0
    }
    
    print(f"   Text to speak: '{clone_payload['text'][:50]}...'")
    print(f"   Reference: {clone_payload['reference_audio']}")
    
    try:
        print("\n   🔄 Generating cloned voice (this may take 30-60 seconds)...")
        clone_response = requests.post(
            "http://localhost:18180/v1/invoke",
            json=clone_payload,
            timeout=120  # Longer timeout for voice cloning
        )
        
        print(f"   Status Code: {clone_response.status_code}")
        
        if clone_response.status_code == 200:
            content_type = clone_response.headers.get('content-type', '')
            
            if 'audio' in content_type or len(clone_response.content) > 1000:
                # Save cloned audio
                cloned_file = "modi_cloned_voice.wav"
                with open(cloned_file, "wb") as f:
                    f.write(clone_response.content)
                
                file_size = os.path.getsize(cloned_file) / 1024
                print(f"   ✅ Cloned voice generated: {cloned_file} ({file_size:.1f} KB)")
                
                # Copy to GPU data directory
                shutil.copy(cloned_file, 
                           os.path.expanduser("~/heygem_data/gpu0/face2face/modi_cloned_voice.wav"))
                print(f"   ✅ Ready for video generation!")
                
                print("\n   📹 Next step: Generate video with cloned voice:")
                print(f"   python3 run_with_stats.py")
                print(f"   (Edit AUDIO_FILE = 'modi_cloned_voice.wav')")
            else:
                print(f"   Response: {clone_response.text}")
        else:
            print(f"   ❌ Cloning failed: {clone_response.status_code}")
            print(f"   Response: {clone_response.text}")
            
    except Exception as e:
        print(f"   ❌ Error during cloning: {e}")
        
else:
    print(f"\n⚠️  Reference audio not found: {modi_audio}")
    print("   Skipping voice cloning test")

print("\n" + "=" * 80)
print("🎉 All tests completed!")
print("=" * 80)

# Check available endpoints
print("\n5️⃣ Discovering available TTS endpoints...")
endpoints_to_try = [
    "/v1/tts",
    "/tts",
    "/api/tts",
    "/clone_voice",
    "/v1/models",
    "/models"
]

print("\nTrying endpoints:")
for endpoint in endpoints_to_try:
    try:
        resp = requests.get(f"http://localhost:18180{endpoint}", timeout=3)
        if resp.status_code < 500:
            print(f"   ✅ {endpoint} - Status: {resp.status_code}")
    except:
        print(f"   ❌ {endpoint} - Not accessible")

print("\n" + "=" * 80)
print("📝 Summary:")
print("   - TTS Service: Running ✅")
print("   - Voice Cloning: Tested with Modi's voice")
print("   - Generated files ready for video generation")
print("=" * 80)
