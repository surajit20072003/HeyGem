# Multi-GPU Video Generation System - Quick Start

## 🚀 System Ready!

Your multi-GPU video generation system is now complete!

### ✅ What's Built:

**Backend:**
- Simple GPU Scheduler (1 task per GPU)
- Flask API Server (Port 5000)
- TTS Voice Cloning Integration
- Automatic queue management

**Frontend:**
- Modern web interface
- Drag & drop video upload
- Real-time GPU status
- Task progress monitoring
- Download completed videos

---

## 📁 File Structure

```
/nvme0n1-disk/HeyGem/webapp/
├── app.py                  # Flask API server
├── gpu_scheduler.py        # GPU scheduling logic  
├── requirements.txt        # Python dependencies
├── static/
│   └── index.html          # Web interface
├── uploads/                # User uploaded videos
├── outputs/                # Generated videos
└── temp/                   # Temporary audio files
```

---

## 🎬 How to Start

### Step 1: Install Dependencies
```bash
cd /nvme0n1-disk/HeyGem/webapp
pip install -r requirements.txt
```

### Step 2: Start the Server
```bash
python3 app.py
```

### Step 3: Open Browser
```
http://localhost:5000
```

---

## 🔄 Workflow

1. **Upload Video:** User drags video file
2. **Enter Text:** Text to speak (voice cloned from video)
3. **Submit:** Click "Generate Video"

**Behind the scenes:**
- Extract audio from video → Use as reference
- Generate voice clone using TTS
- Find available GPU or add to queue
- Generate talking head video  
- Download when ready

---

## 🎯 GPU Logic

- **GPU 0** (Port 8390): 1 video max
- **GPU 1** (Port 8391): 1 video max  
- **GPU 2** (Port 8392): 1 video max

**Total:** 3 videos parallel

**Queue:** If all GPUs busy → automatic queue → processes when GPU frees

---

## 🧪 Testing

Test with curl:
```bash
# Upload and generate
curl -X POST http://localhost:5000/api/generate \
  -F "video=@test.mp4" \
  -F "text=Hello this is a test"

# Check status
curl http://localhost:5000/api/status/task_xxxxx

# Download result
curl http://localhost:5000/api/download/task_xxxxx -o result.mp4
```

---

## ✨ Ready to Use!

Sab kuch ready hai! Ab aap:
1. Server start karo (`python3 app.py`)
2. Browser open karo (`http://localhost:5000`)
3. Video upload karke test karo

GPU status real-time update hota rahega! 🎉
