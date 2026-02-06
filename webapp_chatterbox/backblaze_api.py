import os
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from b2sdk.v2.exception import B2Error

class BackblazeUploader:
    def __init__(self, config):
        """
        Initialize Backblaze B2 uploader with credentials from config.
        
        Args:
            config (dict): Configuration containing:
                - application_key_id: B2 application key ID
                - application_key: B2 application key
                - bucket_name: Name of the B2 bucket
                - bucket_id: ID of the B2 bucket (optional, will be fetched if not provided)
        """
        self.config = config
        self.application_key_id = config.get("application_key_id")
        self.application_key = config.get("application_key")
        self.bucket_name = config.get("bucket_name")
        self.bucket_id = config.get("bucket_id")
        
        # Initialize B2 API
        self.info = InMemoryAccountInfo()
        self.b2_api = B2Api(self.info)
        
    def _authenticate(self):
        """Authenticate with B2 and get bucket reference."""
        if not self.application_key_id or self.application_key_id == "YOUR_KEY_ID":
            print("⚠️ Backblaze B2 credentials not configured.")
            return None
            
        try:
            # Authorize the account
            self.b2_api.authorize_account("production", self.application_key_id, self.application_key)
            
            # Get bucket
            if self.bucket_id:
                bucket = self.b2_api.get_bucket_by_id(self.bucket_id)
            else:
                bucket = self.b2_api.get_bucket_by_name(self.bucket_name)
                
            return bucket
            
        except B2Error as e:
            print(f"❌ B2 Authentication Error: {e}")
            return None
    
    def upload_video(self, file_path, file_name):
        """
        Upload video file to Backblaze B2 bucket.
        
        Args:
            file_path (str): Local path to the video file
            file_name (str): Name to use for the file in B2
            
        Returns:
            str: Public download URL if successful, None otherwise
        """
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None
            
        print(f"📤 Uploading to Backblaze B2: {file_name}...")
        
        try:
            # Authenticate and get bucket
            bucket = self._authenticate()
            if not bucket:
                return None
            
            # Upload the file
            file_info = bucket.upload_local_file(
                local_file=file_path,
                file_name=file_name,
                content_type='video/mp4'
            )
            
            # Generate public download URL
            download_url = self.b2_api.get_download_url_for_file_name(
                bucket_name=self.bucket_name,
                file_name=file_name
            )
            
            print(f"✅ B2 Upload Complete! File ID: {file_info.id_}")
            
            return download_url
            
        except B2Error as e:
            print(f"❌ B2 Upload Error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected Upload Error: {e}")
            return None
    
    def delete_file(self, file_name):
        """
        Delete a file from B2 bucket (optional cleanup method).
        
        Args:
            file_name (str): Name of the file to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            bucket = self._authenticate()
            if not bucket:
                return False
                
            # Get file version
            file_version = bucket.get_file_info_by_name(file_name)
            
            # Delete the file
            self.b2_api.delete_file_version(file_version.id_, file_name)
            
            print(f"🗑️ Deleted file from B2: {file_name}")
            return True
            
        except B2Error as e:
            print(f"⚠️ Could not delete file: {e}")
            return False
    
    def get_file_url(self, file_name):
        """
        Get public download URL for a file.
        
        Args:
            file_name (str): Name of the file in B2
            
        Returns:
            str: Public download URL
        """
        try:
            bucket = self._authenticate()
            if not bucket:
                return None
                
            download_url = self.b2_api.get_download_url_for_file_name(
                bucket_name=self.bucket_name,
                file_name=file_name
            )
            
            return download_url
            
        except Exception as e:
            print(f"⚠️ Could not generate URL: {e}")
            return None
