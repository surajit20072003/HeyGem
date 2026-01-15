#!/usr/bin/env python3
"""
Simple Vimeo Upload Test
"""
import sys
import vimeo

# Configuration
CLIENT_ID = "dca4c491c5bac1f0619df145bcca3e47791108cd"
CLIENT_SECRET = "8R6A46tJ9E+1GIv9fySV+Z5/2SkXVHSowhSicLoh8ibWPbF4Tk8cUiIrJ2iE74JbX47oTYon8vV33sAnazTlcHxqPyayLpljl5y6WmN6F6y33ByHmyoXpthRkeqQzWyU"
ACCESS_TOKEN = "66b9924a59f44740dc427fd91f633b84"

def test_upload(video_path):
    """Test Vimeo upload with new token"""
    print(f"\n{'='*60}")
    print(f"🎬 Testing Vimeo Upload")
    print(f"{'='*60}")
    print(f"Video: {video_path}")
    
    try:
        # Initialize client
        client = vimeo.VimeoClient(
            token=ACCESS_TOKEN,
            key=CLIENT_ID,
            secret=CLIENT_SECRET
        )
        
        print(f"📤 Uploading to Vimeo...")
        
        # Upload
        uri = client.upload(video_path, data={
            'name': 'HeyGem Test Upload',
            'description': 'Test video from Triple GPU system',
            'privacy': {'view': 'anybody'}  # Public
        })
        
        print(f"✅ Upload Successful!")
        print(f"   URI: {uri}")
        
        # Get video link
        video_data = client.get(uri + '?fields=link,name').json()
        print(f"   Link: {video_data.get('link')}")
        print(f"   Name: {video_data.get('name')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_vimeo_upload.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    success = test_upload(video_path)
    sys.exit(0 if success else 1)
