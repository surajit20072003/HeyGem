import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import pickle
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

class YouTubeUploader:
    def __init__(self, config):
        self.config = config
        self.client_secrets_file = config.get("client_secrets_file")
        self.token_file = config.get("token_file")
        self.scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        self.api_service_name = "youtube"
        self.api_version = "v3"

    def get_authenticated_service(self):
        credentials = None
        
        # Load existing credentials
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    credentials = pickle.load(token)
            except Exception as e:
                print(f"⚠️ Failed to load token: {e}")

        # Refresh or Create new credentials
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    print(f"⚠️ Refresh failed: {e}. Re-authenticating...")
                    credentials = None
            
            if not credentials:
                if not os.path.exists(self.client_secrets_file):
                    print("❌ Error: client_secrets.json not found for YouTube.")
                    return None
                
                # Manual Flow for Headless Server
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, self.scopes)
                
                # Use OOB flow
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                
                print("\n" + "="*60)
                print("🔵 Manual Authentication Required")
                print("Please visit this URL to authorize:")
                print(f"\n{auth_url}\n")
                print("="*60 + "\n")
                
                code = input("Enter the authorization code here: ").strip()
                flow.fetch_token(code=code)
                credentials = flow.credentials

                # Save credentials
                with open(self.token_file, 'wb') as token:
                    pickle.dump(credentials, token)

        return googleapiclient.discovery.build(
            self.api_service_name, self.api_version, credentials=credentials)

    def upload_video(self, file_path, title, description):
        youtube = self.get_authenticated_service()
        if not youtube:
            return False

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["HeyGem", "AI Video"],
                "categoryId": "22" # People & Blogs
            },
            "status": {
                "privacyStatus": self.config.get("privacy_status", "private")
            }
        }

        print(f"📤 Uploading to YouTube: {title}...")
        
        try:
            media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"   Upload progress: {int(status.progress() * 100)}%")
            
            print(f"✅ YouTube Upload Complete! Video ID: {response.get('id')}")
            return True
            
        except googleapiclient.errors.HttpError as e:
            print(f"❌ YouTube API Error: {e}")
            return False
        except Exception as e:
            print(f"❌ YouTube Upload Error: {e}")
            return False
