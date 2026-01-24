#!/usr/bin/env python3
"""
Test script to check if Vimeo account supports direct MP4 links
"""
import json
import vimeo

# Load config
with open('webapp_dual_tts/vimeo_config.json', 'r') as f:
    config = json.load(f)

client = vimeo.VimeoClient(
    token=config['access_token'],
    key=config['client_id'],
    secret=config['client_secret']
)

# Test with the recent video
video_uri = '/videos/1154575321'

print(f"🔍 Testing Vimeo API for: {video_uri}")
print(f"📋 Checking account capabilities...\n")

try:
    response = client.get(video_uri)
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ API Response Status: {response.status_code}")
        print(f"📊 Available fields: {list(data.keys())}\n")
        
        if 'files' in data:
            print("✅ 'files' field is available!")
            print(f"📹 Found {len(data['files'])} video files:")
            for file in data['files']:
                print(f"   - {file.get('quality')} ({file.get('type')}) - {file.get('width')}x{file.get('height')}")
                if file.get('type') == 'video/mp4':
                    print(f"     🔗 Link: {file.get('link')[:80]}...")
        else:
            print("❌ 'files' field NOT available")
            print("⚠️  This means your Vimeo account is likely on a FREE or BASIC plan")
            print("💡 Direct MP4 links require a PAID plan (Standard/Pro/Business/Premium)")
            
        # Check download field
        if 'download' in data:
            print(f"\n✅ 'download' field available:")
            for item in data['download']:
                print(f"   - {item.get('quality')} ({item.get('type')})")
        else:
            print("\n❌ 'download' field also not available")
            
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
