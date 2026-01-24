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
            return None
            
        client = vimeo.VimeoClient(
            token=self.access_token,
            key=self.client_id,
            secret=self.client_secret
        )
        
        print(f"📤 Uploading to Vimeo: {title}...")
        
        try:
            uri = client.upload(file_path, data={
                'name': title,
                'description': description,
                'privacy': {
                    'view': 'anybody',
                    'embed': 'public'
                }
            })
            
            print(f"✅ Vimeo Upload Complete! URI: {uri}")
            
            # Return URI for link generation
            return uri
            
        except Exception as e:
            print(f"❌ Vimeo Upload Error: {e}")
            return None

    def get_direct_link(self, uri):
        """Fetch the direct MP4 link for a video (Requires paid plan + correct scopes)"""
        if not self.access_token:
            return None
            
        client = vimeo.VimeoClient(
            token=self.access_token,
            key=self.client_id,
            secret=self.client_secret
        )
        
        try:
            # Get video details
            response = client.get(uri)
            if response.status_code == 200:
                data = response.json()
                
                # Check for 'files' key (available on paid plans)
                if 'files' in data:
                    # Sort by width (resolution) descending to get best quality
                    files = sorted(data['files'], key=lambda x: x.get('width', 0), reverse=True)
                    
                    # Find first mp4
                    for file in files:
                        if file.get('type') == 'video/mp4':
                            return file.get('link')
                            
            return None
        except Exception as e:
            print(f"⚠️ Could not fetch direct link: {e}")
            return None
