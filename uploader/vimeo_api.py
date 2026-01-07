import os
import vimeo

class VimeoUploader:
    def __init__(self, config):
        self.config = config
        self.access_token = config.get("access_token")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")

    def upload_video(self, file_path, title, description):
        if not self.access_token or self.access_token == "YOUR_VIMEO_ACCESS_TOKEN":
            print("⚠️ Vimeo access token not configured.")
            return False
            
        client = vimeo.VimeoClient(
            token=self.access_token,
            key=self.client_id,
            secret=self.client_secret
        )
        
        print(f"📤 Uploading to Vimeo: {title}...")
        
        try:
            uri = client.upload(file_path, data={
                'name': title,
                'description': description
            })
            
            print(f"✅ Vimeo Upload Complete! URI: {uri}")
            
            # Optional: Verify upload or get link
            # video_data = client.get(uri + '?fields=link').json()
            # print(f"   Link: {video_data.get('link')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Vimeo Upload Error: {e}")
            return False
