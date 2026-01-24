import requests
import time
import os
import json

TTS_URL = "http://localhost:18182/v1/invoke"
REF_AUDIO = "/nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts/reference_audio.wav"
TEXT = "This is a test sentence to check if the speed parameter works successfully."

def test_tts(params, name):
    payload = {
        "text": TEXT,
        "reference_audio": params.get('reference_audio', "/code/data/reference/reference_audio.wav"),
        "reference_text": "",
        "format": "wav"
    }
    # Add extra params
    for k, v in params.items():
        if k != 'reference_audio':
            payload[k] = v
            
    print(f"\n🧪 Testing {name} with params: {json.dumps(payload, indent=2)}")
    
    start = time.time()
    try:
        response = requests.post(TTS_URL, json=payload, timeout=60)
        duration = time.time() - start
        
        if response.status_code == 200:
            filename = f"test_{name}.wav"
            with open(filename, 'wb') as f:
                f.write(response.content)
            size = os.path.getsize(filename)
            print(f"✅ Success! Size: {size} bytes, Time: {duration:.2f}s")
            return size
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

# Ensure raw ref audio exists in the mapped volume for the container if needed, 
# but previous usage implies /code/data/reference/ is mapped.
# Let's assume standard params first.

print("--- Baseline ---")
base_size = test_tts({}, "baseline")

print("\n--- Speed 1.5 Test ---")
fast_size = test_tts({"speed": 1.5}, "fast_1_5")

print("\n--- Speed 2.0 Test ---")
faster_size = test_tts({"speed": 2.0}, "fast_2_0")

print("\n--- Language Test (hi) ---")
test_tts({"language": "hi"}, "lang_hi")

# Compare
if base_size > 0:
    print("\n📊 Analysis:")
    print(f"Baseline Size: {base_size}")
    print(f"Speed 1.5 Size: {fast_size}")
    
    if abs(base_size - fast_size) < 1000: # Allow small variance
        print("⚠️  Sizes are identical. 'speed' parameter is LIKELY IGNORED.")
    else:
        if fast_size < base_size:
            print("✅ Fast size is smaller. 'speed' parameter WORKS!")
        else:
            print("❓ Sizes differ significantly but fast is not smaller?")
