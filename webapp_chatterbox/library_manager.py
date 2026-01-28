import os
import json
import shutil
import time
import uuid
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LibraryManager:
    def __init__(self, base_path):
        """
        Initialize LibraryManager
        base_path: Absolute path to webapp_chatterbox directory
        """
        self.base_path = base_path
        self.library_dir = os.path.join(base_path, 'library')
        self.meta_file = os.path.join(self.library_dir, 'meta.json')
        
        # Ensure library directory exists
        os.makedirs(self.library_dir, exist_ok=True)
        
        # Initialize meta.json if it doesn't exist
        if not os.path.exists(self.meta_file):
            self._save_meta({})

    def _load_meta(self):
        """Load metadata from JSON file"""
        try:
            with open(self.meta_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading meta.json: {e}")
            return {}

    def _save_meta(self, data):
        """Save metadata to JSON file"""
        try:
            with open(self.meta_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving meta.json: {e}")

    def add_avatar(self, video_path, audio_path, name=None):
        """
        Add a new avatar to the library
        video_path: Path to the source video file
        audio_path: Path to the extracted audio file
        name: User-friendly name for the avatar
        """
        avatar_uuid = str(uuid.uuid4())[:8]  # Short 8-char UUID
        avatar_id = f"avatar_{avatar_uuid}"
        
        # Create directory for this avatar
        avatar_dir = os.path.join(self.library_dir, avatar_id)
        os.makedirs(avatar_dir, exist_ok=True)
        
        # Define destination paths
        dest_video = os.path.join(avatar_dir, 'source.mp4')
        dest_audio = os.path.join(avatar_dir, 'audio.wav')
        
        try:
            # Copy files
            shutil.copy2(video_path, dest_video)
            shutil.copy2(audio_path, dest_audio)
            
            # Update metadata
            meta = self._load_meta()
            meta[avatar_id] = {
                "id": avatar_id,
                "name": name or f"Avatar {avatar_uuid}",
                "created_at": datetime.now().isoformat(),
                "paths": {
                    "video": f"library/{avatar_id}/source.mp4",
                    "audio": f"library/{avatar_id}/audio.wav"
                }
            }
            self._save_meta(meta)
            
            logger.info(f"Avatar added: {avatar_id} ({name})")
            return {
                "success": True,
                "avatar_id": avatar_id,
                "name": meta[avatar_id]["name"]
            }
            
        except Exception as e:
            logger.error(f"Failed to add avatar: {e}")
            # Cleanup on failure
            if os.path.exists(avatar_dir):
                shutil.rmtree(avatar_dir)
            return {"success": False, "error": str(e)}

    def list_avatars(self):
        """List all available avatars (sorted by newest first)"""
        meta = self._load_meta()
        avatars = list(meta.values())
        # Sort by creation date descending
        avatars.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return avatars

    def get_avatar_paths(self, avatar_id):
        """
        Get absolute paths for an avatar's assets
        Returns (video_path, audio_path) or (None, None)
        """
        meta = self._load_meta()
        if avatar_id not in meta:
            return None, None
            
        rel_video = meta[avatar_id]["paths"]["video"]
        rel_audio = meta[avatar_id]["paths"]["audio"]
        
        abs_video = os.path.join(self.base_path, "..", rel_video) # Adjusting relative to base (webapp_chatterbox)
        abs_audio = os.path.join(self.base_path, "..", rel_audio)
        
        # Correct path construction: stored relative paths are like "library/..."
        # base_path is ".../webapp_chatterbox"
        # So join direct
        abs_video = os.path.join(self.base_path, rel_video.replace('library/', 'library/'))
        abs_audio = os.path.join(self.base_path, rel_audio.replace('library/', 'library/'))
        
        # Actually easier to just use the library dir structure knoweldge
        abs_video = os.path.join(self.library_dir, avatar_id, 'source.mp4')
        abs_audio = os.path.join(self.library_dir, avatar_id, 'audio.wav')

        if not os.path.exists(abs_video) or not os.path.exists(abs_audio):
            logger.warning(f"Files missing for {avatar_id}")
            return None, None
            
        return abs_video, abs_audio

    def delete_avatar(self, avatar_id):
        """Delete an avatar and its files"""
        meta = self._load_meta()
        if avatar_id in meta:
            # Remove directory
            avatar_dir = os.path.join(self.library_dir, avatar_id)
            if os.path.exists(avatar_dir):
                shutil.rmtree(avatar_dir)
            
            # Remove from meta
            del meta[avatar_id]
            self._save_meta(meta)
            return True
        return False
