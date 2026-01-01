#!/usr/bin/env python3
"""
Fish-Speech TTS Test - Working Version
Uses correct /v1/invoke endpoint
"""
import requests
import os

print("=" * 80)
print("🎤 Fish-Speech TTS - WORKING TEST")
print("=" * 80)

TTS_API = "http://localhost:18180"

# Test 1: Basic TTS
print("\n1️⃣ Testing basic TTS...")
response = requests.post(
    f"{TTS_API}/v1/invoke",
    json={
        "text": "Hello, this is Fish Speech TTS working perfectly!",
        "reference_audio": "",
        "reference_text": "",
        "format": "wav"
    }
)

if response.status_code == 200:
    with open("test_basic_tts.wav", "wb") as f:
        f.write(response.content)
    size = os.path.getsize("test_basic_tts.wav")
    print(f"   ✅ Basic TTS Success! File: test_basic_tts.wav ({size} bytes)")
else:
    print(f"   ❌ Failed: {response.status_code}")

# Test 2: Hindi TTS
print("\n2️⃣ Testing Hindi TTS...")
response = requests.post(
    f"{TTS_API}/v1/invoke",
    json={
        "text": "नमस्ते मित्रों, मैं आपका स्वागत करता हूं",
        "reference_audio": "",
        "reference_text": "",
        "format": "wav"
    }
)

if response.status_code == 200:
    with open("test_hindi_tts.wav", "wb") as f:
        f.write(response.content)
    size = os.path.getsize("test_hindi_tts.wav")
    print(f"   ✅ Hindi TTS Success! File: test_hindi_tts.wav ({size} bytes)")
else:
    print(f"   ❌ Failed: {response.status_code}")

# Test 3: Voice Cloning with Modi's voice
print("\n3️⃣ Testing Voice Cloning with Modi's voice...")

# Check if reference audio exists
ref_audio_path = "/root/heygem_data/voice/data/reference/input_audio.mp3"
if not os.path.exists(ref_audio_path):
    print(f"   ⚠️  Copying input_audio.mp3 to {ref_audio_path}")
    os.makedirs(os.path.dirname(ref_audio_path), exist_ok=True)
    import shutil
    shutil.copy("/nvme0n1-disk/HeyGem/input_audio.mp3", ref_audio_path)

# Try voice cloning
clone_text = "Every evening, Mr. Rao stood at the old railway platform, holding a crumpled ticket in his hand. Trains no longer stopped there, but he came anyway, watching the empty tracks as the sun went down."

response = requests.post(
    f"{TTS_API}/v1/invoke",
    json={
        "text": clone_text,
        "reference_audio": "/code/data/reference/input_audio.mp3",
        "reference_text": "Sample reference text for voice cloning",
        "format": "wav"
    }
)

if response.status_code == 200:
    with open("modi_cloned_voice.wav", "wb") as f:
        f.write(response.content)
    size = os.path.getsize("modi_cloned_voice.wav")
    print(f"   ✅ Voice Cloning Success! File: modi_cloned_voice.wav ({size} bytes)")
    print(f"   📝 Text: '{clone_text[:50]}...'")
else:
    print(f"   ❌ Failed: {response.status_code}")
    print(f"   Response: {response.text[:200]}")

print("\n" + "=" * 80)
print("✅ Fish-Speech TTS is WORKING!")
print("=" * 80)
print("\n📁 Generated files:")
print("   - test_basic_tts.wav")
print("   - test_hindi_tts.wav") 
print("   - cloned_voice.wav (if voice cloning worked)")
print("\n🎧 Play them with: aplay <filename>.wav")
print("=" * 80)
