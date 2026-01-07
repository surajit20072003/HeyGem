#!/usr/bin/env python3
import sys
import os
import json
import argparse
from datetime import datetime
from youtube_api import YouTubeUploader
from vimeo_api import VimeoUploader

# Configuration Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Config file not found: {CONFIG_FILE}")
        return None
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def format_string(template, filename, task_id):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return template.format(
        filename=filename,
        task_id=task_id,
        date=date_str
    )

def main():
    parser = argparse.ArgumentParser(description="HeyGem Auto-Uploader")
    parser.add_argument("file_path", help="Path to the video file")
    parser.add_argument("--task_id", default="unknown", help="Task ID associated with the video")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_path):
        print(f"❌ File not found: {args.file_path}")
        sys.exit(1)
        
    config = load_config()
    if not config:
        sys.exit(1)
        
    filename = os.path.basename(args.file_path)
    print(f"\n{'='*60}")
    print(f"🚀 Starting Auto-Upload for: {filename}")
    print(f"{'='*60}")

    # YouTube Upload
    yt_config = config.get("youtube", {})
    if yt_config.get("enabled"):
        title = format_string(yt_config.get("title_template", "{filename}"), filename, args.task_id)
        desc = format_string(yt_config.get("description_template", ""), filename, args.task_id)
        
        uploader = YouTubeUploader(yt_config)
        uploader.upload_video(args.file_path, title, desc)
    else:
        print("⏭️  YouTube upload disabled in config.")

    # Vimeo Upload
    vim_config = config.get("vimeo", {})
    if vim_config.get("enabled"):
        title = format_string(vim_config.get("name_template", "{filename}"), filename, args.task_id)
        desc = format_string(vim_config.get("description_template", ""), filename, args.task_id)
        
        uploader = VimeoUploader(vim_config)
        uploader.upload_video(args.file_path, title, desc)
    else:
        print("⏭️  Vimeo upload disabled in config.")
        
    print(f"\n{'-'*60}")
    print("🏁 Upload process finished.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
