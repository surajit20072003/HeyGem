#!/usr/bin/env python3
"""
Quick HeyGem API Test - Simple Demo
"""
import requests
import json

# Test if API is working
print("=" * 60)
print("HeyGem.ai API Quick Test")
print("=" * 60)

# Test 1: API Connection
print("\n🔍 Test 1: Checking API connection...")
try:
    response = requests.get("http://127.0.0.1:8383", timeout=5)
    print(f"✅ API is running! (Status: {response.status_code})")
    print(f"   Response type: {response.headers.get('Content-Type', 'unknown')}")
except Exception as e:
    print(f"❌ API not accessible: {e}")
    exit(1)

# Test 2: Available endpoints info
print("\n📡 Test 2: Available API Endpoints:")
print("   POST http://127.0.0.1:8383/easy/submit")
print("   GET  http://127.0.0.1:8383/easy/query?code=<task_code>")

# Test 3: Check data directory
print("\n📁 Test 3: Data directory status:")
import os
data_dir = os.path.expanduser("~/heygem_data/face2face")
if os.path.exists(data_dir):
    print(f"✅ Data directory exists: {data_dir}")
    files = os.listdir(data_dir)
    if files:
        print(f"   Files found: {len(files)}")
        for f in files[:5]:  # Show first 5 files
            print(f"   - {f}")
    else:
        print("   ⚠️  Directory is empty - add audio/video files here")
else:
    print(f"⚠️  Data directory not found: {data_dir}")
    print("   Creating it now...")
    os.makedirs(data_dir, exist_ok=True)
    print("✅ Created!")

print("\n" + "=" * 60)
print("✅ API is ready to use!")
print("=" * 60)
print("\n📝 Next steps:")
print("1. Put your audio file (.wav) in ~/heygem_data/face2face/")
print("2. Put your face video (.mp4) in ~/heygem_data/face2face/")
print("3. Use the API to generate talking video")
print("\nExample command:")
print("  python3 /nvme0n1-disk/HeyGem/test_heygem_api.py")
print("\n" + "=" * 60)
