# 🎬 HeyGem Dual TTS API Endpoints

**Base URL**: `http://localhost:5003`

---

## 📋 API Endpoints

### 1. **Home Page**
```
GET /
```
**Description**: Serves the web interface  
**Response**: HTML page

---

### 2. **Generate Video**
```
POST /api/generate
```
**Description**: Generate video with voice cloning  
**Request**:
- **Form Data**:
  - `text` (required): Text to convert to speech
  - `video` (optional): Video file (mp4, avi, mov, mkv)
  
**Response**:
```json
{
  "success": true,
  "task_id": "task_1234567890",
  "message": "Task submitted successfully",
  "status_url": "/api/status/task_1234567890"
}
```

---

### 3. **Get Task Status**
```
GET /api/status/<task_id>
```
**Description**: Check status of a video generation task  
**Response**:
```json
{
  "status": "processing|completed|failed|queued",
  "progress": 0-100,
  "gpu_id": 0,
  "error": "error message if failed",
  "result": {...}
}
```

---

### 4. **Download Video**
```
GET /api/download/<task_id>
```
**Description**: Download the generated video  
**Response**: Video file (MP4)

---

### 5. **Queue Status**
```
GET /api/queue
```
**Description**: Get current GPU and queue status  
**Response**:
```json
{
  "gpus": {
    "0": {
      "busy": false,
      "current_task": null,
      "memory_used": "1234 MiB",
      "video_port": 8390,
      "tts_port": 18182
    },
    "1": {...}
  },
  "queue": [...],
  "queue_size": 0
}
```

---

### 6. **API Info**
```
GET /api/info
```
**Description**: Get API service information  
**Response**:
```json
{
  "service": "Dual GPU + Dual TTS Video Generation",
  "version": "1.0.0",
  "port": 5003,
  "gpus": {
    "0": {"video_port": 8390, "tts_port": 18180},
    "1": {"video_port": 8391, "tts_port": 18181}
  },
  "endpoints": [...]
}
```

---

### 7. **Health Check**
```
GET /api/health
```
**Description**: Service health check  
**Response**:
```json
{
  "status": "healthy",
  "service": "Dual GPU + Dual TTS",
  "timestamp": "2026-01-08T19:10:00"
}
```

---

### 8. **Serve Output Files**
```
GET /outputs/<filename>
```
**Description**: Access generated output files  
**Example**: `GET /outputs/final_task_1234567890.mp4`

---

## 📝 Usage Example

### Generate Video with cURL
```bash
curl -X POST http://localhost:5003/api/generate \
  -F "text=Hello, this is a test message" \
  -F "video=@my_video.mp4"
```

### Check Status
```bash
curl http://localhost:5003/api/status/task_1234567890
```

### Download Video
```bash
curl -O http://localhost:5003/api/download/task_1234567890
```

---

## 🔧 Service Configuration

- **Port**: 5003
- **GPU 0**: Video Port 8390, TTS Port 18182
- **GPU 1**: Video Port 8391, TTS Port 18183
- **Max Concurrent Tasks**: 2 (one per GPU)
- **Queue**: Unlimited

---

## ⚙️ Features

✅ **Text Normalization**: Automatic LaTeX/Math/Number conversion  
✅ **Voice Cloning**: High-quality voice cloning with reference audio  
✅ **Dual GPU**: Parallel processing on 2 GPUs  
✅ **Dedicated TTS**: Each GPU has its own TTS service  
✅ **Queue Management**: Automatic task queuing when GPUs busy  
✅ **File Stability**: 3-check validation before marking complete
