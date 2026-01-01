# Multi-Video Random Merge System

## 🚀 Overview

This webapp **randomly merges multiple input videos** to create natural variation across GPU chunks. Each chunk gets a unique random combination of videos matching the audio duration.

### Key Difference from Other Webapps:
- **Regular webapp** (Port 5000): 1 GPU = 1 video (queue mode)
- **Chunked webapp** (Port 5001): 3 GPUs = 1 video split into chunks
- **Multi-video webapp** (Port 5002): **3 GPUs = Random merge of multiple videos**

---

## 📁 File Structure

```
webapp_multi_video/
├── app.py                      # Flask API (Port 5002)
├── multi_video_scheduler.py    # Random merge scheduler
├── requirements.txt            # Dependencies
├── static/
│   └── index.html             # Web UI
├── input_videos/              # User uploaded videos
├── uploads/                   # Reference audios
├── outputs/                   # Final merged videos
└── temp/                      # Temporary files
```

---

## 🎬 How It Works

### Input:
1. **Multiple videos** (e.g., 5 different face videos)
2. **Reference audio** (for voice cloning)
3. **Text** (to convert to speech)

### Process:
1. Text → TTS → Cloned audio
2. Audio split → 3 chunks (e.g., 10s + 10s + 10s)
3. **For each chunk:**
   - Randomly select videos from input pool
   - Merge until chunk duration is met
   - Example: Chunk 1 (10s) = video2 (4s) + video5 (3s) + video1 (3s)
4. Submit 3 merged videos to 3 GPUs
5. Final merge

### Result:
- **No repetitive patterns**
- **Natural variation** across video
- **Unique combinations** per chunk

---

## 🎯 Example

**Input Videos:**
- video1.mp4 (5 seconds)
- video2.mp4 (8 seconds)
- video3.mp4 (6 seconds)
- video4.mp4 (4 seconds)

**Audio:** 30 seconds total → 3 chunks of 10s each

**Random Merge:**
- **Chunk 1 (10s)**: `video3 (6s) + video1 (4s)` → GPU 0
- **Chunk 2 (10s)**: `video4 (4s) + video2 (6s)` → GPU 1
- **Chunk 3 (10s)**: `video1 (5s) + video3 (5s)` → GPU 2

**Output:** Natural-looking video with varied expressions!

---

## 🚀 How to Start

```bash
cd /nvme0n1-disk/HeyGem/webapp_multi_video
pip install -r requirements.txt
python3 app.py
```

Open: **http://localhost:5002**

---

## 🎨 UI Features

- **Multiple video upload** with drag & drop
- **Reference audio upload**
- **Real-time GPU status**
- **Task progress tracking**
- **Download final video**

---

## 🔧 Technical Details

**Port:** 5002
**Mode:** Random video merge + 3 GPU parallel

**Algorithm:**
```python
1. Shuffle input videos randomly
2. For target duration:
   - Pick next video from shuffled list
   - If full video fits → add it
   - If partial needed → trim and add
   - Track used segments
3. Concatenate selected segments
4. Submit to GPU
```

**Benefits:**
- Natural variation
- No visible loops
- Efficient use of limited video assets

---

## ✅ Ready to Test!

System complete aur ready hai. Teen webapp ab available hain:

- **Port 5000** → Queue mode (multiple jobs)
- **Port 5001** → Chunked mode (fast single video)
- **Port 5002** → Random merge (natural variation)

Choose based on your use case! 🎉
