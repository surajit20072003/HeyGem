# Chunked Multi-GPU Video Generation System

## 🚀 Overview

This is a **separate** video generation system that uses **chunked parallel processing** across all 3 GPUs simultaneously. Unlike the regular webapp (which processes 1 video per GPU), this system:

1. **Splits audio** into 3 equal chunks
2. **Processes all 3 chunks in parallel** (GPU 0, 1, 2 simultaneously)
3. **Merges** the results into a final video

**Perfect for:** Long videos where speed is critical!

---

## 📁 File Structure

```
/nvme0n1-disk/HeyGem/webapp_chunked/
├── app.py                  # Flask API server (Port 5001)
├── chunked_scheduler.py    # Chunked GPU scheduling logic  
├── requirements.txt        # Python dependencies
├── static/
│   └── index.html          # Web interface (pink/red theme)
├── uploads/                # User uploaded videos
├── outputs/                # Generated videos (merged)
└── temp/                   # Temporary audio chunks
```

---

## 🎬 How to Start

### Step 1: Install Dependencies
```bash
cd /nvme0n1-disk/HeyGem/webapp_chunked
pip install -r requirements.txt
```

### Step 2: Start the Server
```bash
python3 app.py
```

### Step 3: Open Browser
```
http://localhost:5001
```

---

## 🔄 Workflow

1. **Upload Video:** Drag and drop video file
2. **Enter Text:** Text to speak (voice cloned from video)
3. **Submit:** Click "Generate Video (Chunked Mode)"

**Behind the scenes:**
- Extract audio from video → Use as reference
- Generate voice clone using TTS
- **Split cloned audio into 3 equal chunks** ✨
- **Submit all 3 chunks to GPUs simultaneously** (GPU 0, 1, 2) ✨
- **Wait for all chunks to complete** ✨
- **Merge 3 video segments with GPU-accelerated FFmpeg** ✨
- Download final video

---

## 🎯 GPU Logic

**Chunked Mode:**
- GPU 0 → Chunk 1 (0% - 33% of audio)
- GPU 1 → Chunk 2 (33% - 66% of audio)
- GPU 2 → Chunk 3 (66% - 100% of audio)

**All 3 GPUs process simultaneously!**

After completion → FFmpeg merges using GPU acceleration (NVENC)

---

## 📊 Comparison: Regular vs Chunked

| Feature | Regular Webapp (Port 5000) | Chunked Webapp (Port 5001) |
|---------|---------------------------|---------------------------|
| **Mode** | Queue-based | Parallel chunks |
| **GPUs per video** | 1 GPU | 3 GPUs (all) |
| **Parallel videos** | Up to 3 videos | 1 video (3 chunks) |
| **Best for** | Multiple short videos | Single long video |
| **Speed** | Standard | Faster for long content |
| **Queue** | FIFO queue | Single task at a time |

---

## 🧪 Testing

Test with curl:
```bash
# Upload and generate (chunked mode)
curl -X POST http://localhost:5001/api/generate \
  -F "video=@test.mp4" \
  -F "text=This is a long text for testing chunked processing. The audio will be split into three equal parts and processed in parallel across all three GPUs simultaneously."

# Check status
curl http://localhost:5001/api/status/chunked_xxxxx

# Check GPU status
curl http://localhost:5001/api/gpu-status

# Download result
curl http://localhost:5001/api/download/chunked_xxxxx -o result.mp4
```

---

## ⚡ Performance

**Expected speedup for long videos:**
- 1 minute video: ~3x faster
- 3 minute video: ~3x faster
- 5 minute video: ~3x faster

**Note:** Speedup depends on merging overhead. For very short videos (<30s), regular mode might be faster due to splitting/merging overhead.

---

## 🎨 UI Features

- **Pink/Red gradient theme** (different from regular webapp's purple)
- **Real-time GPU status** for all 3 GPUs
- **Chunk progress display** showing individual chunk processing
- **Status indicators**: Splitting → Processing → Merging → Completed

---

## 🔧 Technical Details

**Port:** 5001 (different from regular webapp on 5000)

**GPU Configuration:**
- GPU 0: Port 8390 (Chunk 1)
- GPU 1: Port 8391 (Chunk 2)
- GPU 2: Port 8392 (Chunk 3)

**Processing Steps:**
1. Voice cloning (TTS @ port 18181)
2. Audio splitting (FFmpeg)
3. Parallel GPU processing (3 tasks)
4. GPU-accelerated merging (NVENC)

**File Locations:**
- Uploads: `/nvme0n1-disk/HeyGem/webapp_chunked/uploads/`
- Outputs: `/nvme0n1-disk/HeyGem/webapp_chunked/outputs/`
- Temp chunks: `/nvme0n1-disk/HeyGem/webapp_chunked/temp/`
- GPU data: `~/heygem_data/gpu{0,1,2}/`

---

## ✅ Ready to Use!

**Both systems can run simultaneously:**
- Regular webapp: `http://localhost:5000` (purple theme)
- Chunked webapp: `http://localhost:5001` (pink theme)

Choose the right tool for your use case! 🎉

---

## 🐛 Troubleshooting

**Issue:** Merge fails
- **Solution:** Check FFmpeg has NVENC support (`ffmpeg -encoders | grep nvenc`)

**Issue:** Chunks not processing
- **Solution:** Check all 3 GPU containers are running on ports 8390, 8391, 8392

**Issue:** Audio sync issues in merged video
- **Solution:** This is rare, but ensure input video has constant framerate

**Issue:** Port 5001 already in use
- **Solution:** Change port in `app.py` (line 228)
