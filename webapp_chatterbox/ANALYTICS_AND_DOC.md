# Triple GPU + Triple TTS Webapp — Detailed Documentation & Analytics Notes

Path: `/nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts`

Primary reference: `README.md` in the same directory (triple GPU + triple TTS overview, ports, and run steps). This document expands on analytics/ops details; read alongside `README.md` for the full picture.

## 1) What this service does
- Flask API on port `5003` that accepts text (+ optional video) and returns a `task_id`.
- Coordinates 3 GPU video-generation containers and 3 dedicated TTS containers (ports: GPU 0 → 8390/18182, GPU 1 → 8391/18183, GPU 2 → 8392/18184).
- Extracts audio from user video (or uses default reference audio), normalizes text (LaTeX/math friendly), generates cloned speech via TTS on the same GPU, submits combined audio+video to the GPU container, monitors completion, and copies the final MP4 into `outputs/`.

## 2) Core components (code)
- `app.py`: Flask routes (`/api/generate`, `/api/status/<id>`, `/api/queue`, `/api/download/<id>`, `/api/info`, `/api/health`), request validation, audio extraction via `ffmpeg`, calls into scheduler, launches background threads, and enforces same-GPU TTS+video processing.
- `dual_gpu_scheduler.py`: Triple-GPU scheduler with atomic reservation, queue, submission to GPU containers (`/easy/submit`), status polling (`/easy/query`), file stability checks, result copy into `outputs/`, error/timeout handling, and timing capture (`tts_time`, `video_time`).
- `text_normalization.py`: Converts LaTeX/math and common symbols into speech-friendly text prior to TTS (Greek letters, powers, fractions, sqrt, number-to-words).
- `static/index.html`: Web UI.
- `start.sh`: Convenience runner that checks Docker containers, installs Python deps, and starts the webapp.
- `requirements.txt`: `Flask`, `flask-cors`, `requests`, `psutil`.
- Docs already present: `README.md`, `SYSTEM_LOCATIONS.md`, `API_ENDPOINTS.md`, `COMPLETE_DOCUMENTATION.md`, `QUICKSTART.md`.

## 3) Runtime flow (end-to-end)
1. `POST /api/generate` with `text` (required) and optional `video` file.
2. If video is provided, `ffmpeg` extracts reference audio → `temp/ref_audio_<ts>.wav`; otherwise uses `reference_audio.wav`.
3. Scheduler reserves an available GPU (atomic). If none free, task is enqueued with pre-extracted audio.
4. For the reserved GPU, pick its dedicated TTS port (18182/18183/18184), copy reference audio into `~/heygem_data/tts{gpu}/reference/`, and call TTS `/v1/invoke`. Save generated audio to `temp/tts_<task>.wav`. Fallback to reference audio if TTS fails or output is too small (<10KB).
5. Copy video+audio into `~/heygem_data/gpu{gpu}/` (host path mounted into GPU containers as `/code/data`) and call GPU `/easy/submit` on port 8390/8391/8392 with payload `{audio_url, video_url, code}`.
6. Poll `/easy/query?code=<task>` every 5s (30m timeout). On completion, locate result (strict match `task_*-r.mp4` or reported path), wait for file size stability (3 checks), copy to `outputs/final_<task>.mp4`, and attach `result_url`.
7. Release GPU, then process next queued task. Status and timing are stored in `scheduler.active_tasks`.

## 4) Data/paths and ports
- Web API: `:5003`
- GPU containers: `8390`, `8391`, `8392`
- TTS containers: `18182`, `18183`, `18184`
- Host shared data: `~/heygem_data/gpu{0,1,2}` (videos/audio in/out), `~/heygem_data/tts{0,1,2}/reference` (reference audio per GPU TTS)
- App folders: `uploads/` (incoming videos), `outputs/` (final mp4s), `temp/` (reference + generated audio), `default.mp4`, `reference_audio.wav`

## 5) API behaviors
- `/api/generate` → `202`, returns `task_id`, `status_url`. Rejects missing text or invalid video types (`mp4|avi|mov|mkv`). Defaults to `default.mp4` if no video uploaded. Starts background thread.
- `/api/status/<task_id>` → task status, progress, gpu_id, queue_position, `timing` (`tts_time`, `video_time`, `total_time`), `result` (raw GPU response with `result_url` when found).
- `/api/queue` → GPU busy flags + current task IDs + queue contents (task ids, queued_time, text preview).
- `/api/download/<task_id>` → serves `outputs/<task>_output.mp4` (note: GPU copy uses `final_<task>.mp4`; download route is a TODO/legacy mismatch).
- `/api/info`, `/api/health` → metadata/health responses.

## 6) Resilience and safeguards
- Atomic GPU reservation before TTS prevents cross-GPU mixing.
- Fallbacks: use reference audio if TTS fails or audio too small; use default video if none uploaded.
- File stability checks before copying results; size sanity checks (<100KB → fail).
- Monitoring with max 5 consecutive errors and 30m timeout; on error/timeout, GPU is released and task is marked failed.
- Queue-aware preprocessing status: `scheduler.preprocessing_tasks` shows extraction/TTS steps before GPU submission.

## 7) Observability and “analytics” fields you already get
- In-memory metrics (via `/api/status/<id>`): `progress`, `gpu_id`, `queue_position`, `tts_time`, `video_time`, `total_time`, `input_text`, `reference_audio`, `generated_audio_url`, raw GPU `result`.
- GPU live stats per `get_gpu_status()`: `memory_used` and `gpu_utilization` are pulled from `nvidia-smi` per call.
- Logs: Flask stdout (see service logs), GPU/TTS container logs (`docker logs heygem-gpu*`, `heygem-tts-dual-*`), and file outputs in `~/heygem_data/gpu*/log/` if present.

## 8) How to run
```bash
cd /nvme0n1-disk/nvme01/HeyGem/webapp_dual_tts
# Ensure Docker compose is up at repo root: docker compose -f ../docker-compose-dual-tts.yml up -d
pip install -r requirements.txt
python3 app.py   # or use systemd service heygem-dual-tts
```
Or use `./start.sh` after containers are running; it checks containers, installs deps, and starts the app on `:5003`.

## 9) Operational checks and diagnostics
```bash
docker ps | grep -E "heygem-(gpu|tts)"             # containers up
nvidia-smi                                         # host GPU visibility
docker exec heygem-gpu0 nvidia-smi                 # container GPU visibility
curl -s http://localhost:5003/api/health
curl -s http://localhost:5003/api/queue | jq

# Submit test and watch
curl -X POST http://localhost:5003/api/generate -F "text=diagnostic run" | tee /tmp/heygem_task.json
TASK_ID=$(jq -r '.task_id' /tmp/heygem_task.json)
watch -n 3 "curl -s http://localhost:5003/api/status/$TASK_ID | jq"

# Inspect files (adjust GPU if status shows different one)
ls -lh ~/heygem_data/gpu0 | head
ls -lh outputs | head
```

## 10) Gaps/todos noted during review
- `/api/download/<task_id>` points to `<task>_output.mp4` but scheduler writes `final_<task>.mp4`; align naming.
- No explicit cleanup/rotation for `temp/` and `uploads/`; consider cron/service cleanup.
- No auth/rate limiting on public endpoints.
- No persisted task history (in-memory only).

## 11) If you want richer analytics
- Export `scheduler.active_tasks` snapshots to a store (Redis/SQLite) with timestamps for throughput and error rates.
- Emit Prometheus-friendly metrics (per-GPU busy flag, queue depth, TTS/video durations, failures, timeouts) and scrape.
- Frontend: extend `static/index.html` to poll `/api/queue` + `/api/status` and visualize GPU utilization, queue length, and per-task timings.

## 12) What I need from you to tighten this further
- Confirm actual host paths for `~/heygem_data` (symlink vs real path) and write permissions.
- Confirm Docker compose file in parent dir and image tags used for GPU/TTS containers.
- Provide a sample `docker logs` snippet from one GPU and one TTS container during a run.
- Confirm if `nvidia-smi` is available inside containers and on host.
- If we should fix the download filename mismatch and add temp/cleanup, say so.

## 13) Quick commands you can run now
```bash
docker ps | grep -E "heygem-(gpu|tts)"
nvidia-smi
curl -s http://localhost:5003/api/health
curl -s http://localhost:5003/api/queue | jq
```
