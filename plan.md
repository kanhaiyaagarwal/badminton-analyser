# Plan: AWS S3 Storage & Live Streaming for Badminton Analyzer

## Overview
Extend the badminton analyzer to support:
1. **S3-based storage** - Pre-signed URL uploads, S3 output storage for AWS deployment
2. **Live streaming** - Real-time camera/phone streaming with live analysis

---

## Architecture Diagrams

### Current Architecture (Local Storage)
```
┌──────────┐    Upload video    ┌──────────┐    Save to     ┌──────────┐
│  Client  │ ────────────────▶  │  Server  │ ────────────▶  │  Local   │
│          │                    │          │                │  Disk    │
└──────────┘                    └──────────┘                └──────────┘
```

### New Architecture: S3 Upload Flow
```
┌──────────┐  1. Request upload URL   ┌──────────┐  2. Generate   ┌──────────┐
│  Client  │ ──────────────────────▶  │  Server  │ ────────────▶  │   S3     │
│          │ ◀──────────────────────  │          │ ◀────────────  │          │
│          │  2. Pre-signed URL       │          │  Signed URL    │          │
│          │                          └──────────┘                │          │
│          │  3. Direct upload (multipart)                        │          │
│          │ ─────────────────────────────────────────────────▶  │          │
│          │  4. Upload complete notification                     │          │
│          │ ──────────────────────▶  ┌──────────┐                │          │
└──────────┘                          │  Server  │                └──────────┘
                                      │  (start  │
                                      │  analysis)│
                                      └──────────┘
```

### New Architecture: Live Streaming Flow
```
┌──────────┐                    ┌──────────┐                    ┌──────────┐
│  Client  │  WebSocket frames  │  Server  │  Process frames   │ Analyzer │
│ (Camera) │ ─────────────────▶ │          │ ─────────────────▶│          │
│          │                    │          │                    │          │
│          │ ◀───────────────── │          │ ◀─────────────────│          │
│          │  Live results      │          │  Shot detection   │          │
│          │  (shots, heatmap)  │          │  + positions      │          │
└──────────┘                    └──────────┘                    └──────────┘
                                     │
                                     ▼ (optional)
                                ┌──────────┐
                                │   S3     │  Save recording
                                │          │  + results
                                └──────────┘
```

---

## Part 1: S3 Storage Integration

### New Dependencies
```
boto3>=1.34.0
```

### Configuration Changes (`api/config.py`)

```python
# Add S3 settings
s3_bucket: str = os.getenv("S3_BUCKET", "")
s3_region: str = os.getenv("AWS_REGION", "us-east-1")
s3_upload_prefix: str = "uploads"
s3_output_prefix: str = "analysis_output"
use_s3: bool = bool(os.getenv("S3_BUCKET"))  # Auto-detect S3 mode
cloudfront_domain: str = os.getenv("CLOUDFRONT_DOMAIN", "")  # Optional CDN
```

### New Service: `api/services/s3_service.py`

```python
class S3Service:
    """S3 operations for file storage."""

    def generate_upload_url(user_id: int, filename: str, content_type: str) -> dict:
        """Generate pre-signed URL for direct upload."""
        # Returns: {upload_url, file_key, expires_in}

    def generate_multipart_upload(user_id: int, filename: str) -> dict:
        """For large files (>100MB), initiate multipart upload."""
        # Returns: {upload_id, file_key, part_urls: [...]}

    def complete_multipart_upload(file_key: str, upload_id: str, parts: list):
        """Complete multipart upload after all parts uploaded."""

    def generate_download_url(file_key: str, expires: int = 3600) -> str:
        """Generate pre-signed download URL."""

    def delete_file(file_key: str):
        """Delete file from S3."""

    def copy_to_output(source_key: str, dest_key: str):
        """Copy file within S3 (e.g., for processing)."""
```

### New API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/upload/request` | Get pre-signed upload URL |
| POST | `/api/v1/upload/multipart/init` | Start multipart upload |
| POST | `/api/v1/upload/multipart/complete` | Complete multipart upload |
| POST | `/api/v1/upload/confirm/{job_id}` | Confirm upload complete, create job |

### Database Changes

```python
# Add to Job model
storage_type = Column(String(10), default="local")  # "local" or "s3"
s3_video_key = Column(String(512), nullable=True)   # S3 key for source video
s3_output_prefix = Column(String(512), nullable=True)  # S3 prefix for outputs
```

### Analyzer Service Changes

```python
# Modify run_analysis to handle S3
def run_analysis(
    video_source: str,  # Local path OR S3 URL
    storage_type: str,  # "local" or "s3"
    ...
):
    if storage_type == "s3":
        # Download video to temp file for processing
        # OR stream directly if supported
        video_path = download_from_s3(video_source)

    # ... run analysis ...

    if storage_type == "s3":
        # Upload outputs to S3
        upload_outputs_to_s3(output_dir, s3_output_prefix)
```

### Frontend Changes

**New Component: `S3Uploader.vue`**
- Request pre-signed URL from server
- Upload directly to S3 with progress tracking
- Support chunked/multipart for large files
- Notify server when complete

```javascript
async function uploadToS3(file) {
  // 1. Get pre-signed URL
  const { upload_url, job_id } = await api.post('/api/v1/upload/request', {
    filename: file.name,
    content_type: file.type,
    size: file.size
  })

  // 2. Upload directly to S3 with progress
  await axios.put(upload_url, file, {
    headers: { 'Content-Type': file.type },
    onUploadProgress: (e) => {
      progress.value = (e.loaded / e.total) * 100
    }
  })

  // 3. Confirm upload complete
  await api.post(`/api/v1/upload/confirm/${job_id}`)
}
```

---

## Part 2: Live Streaming Support

### Architecture Components

1. **WebSocket Stream Handler** - Receives frames from client
2. **Stream Analyzer** - Processes frames in real-time
3. **Live Results Broadcaster** - Sends results back to client
4. **Optional Recording** - Saves stream to S3

### New Database Models

```python
class StreamSession(Base):
    """Live streaming session."""
    __tablename__ = "stream_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Court setup (required before streaming)
    court_boundary = Column(JSON)

    # Session state
    status = Column(String(20))  # "setup", "streaming", "ended"
    started_at = Column(DateTime)
    ended_at = Column(DateTime)

    # Recording (optional)
    is_recording = Column(Boolean, default=False)
    recording_s3_key = Column(String(512))

    # Live stats (updated during stream)
    total_shots = Column(Integer, default=0)
    current_rally = Column(Integer, default=0)

    # Results (saved when session ends)
    final_report_path = Column(String(512))
    heatmap_paths = Column(JSON)
```

### New WebSocket Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/ws/stream/{session_id}` | Send video frames, receive analysis |
| `/ws/stream/{session_id}/view` | View-only: receive live results |

### WebSocket Message Protocol

**Client → Server (Frame Data):**
```json
{
  "type": "frame",
  "timestamp": 1234567890.123,
  "data": "<base64 encoded JPEG>",
  "width": 1280,
  "height": 720
}
```

**Server → Client (Analysis Results):**
```json
{
  "type": "shot_detected",
  "shot": "smash",
  "confidence": 0.92,
  "timestamp": 1234567890.123,
  "rally_id": 3
}
```

```json
{
  "type": "position_update",
  "x": 450,
  "y": 320,
  "timestamp": 1234567890.123
}
```

```json
{
  "type": "stats_update",
  "total_shots": 15,
  "current_rally": 3,
  "shot_distribution": {"smash": 5, "clear": 4, ...}
}
```

### New Service: `api/services/stream_service.py`

```python
class StreamAnalyzer:
    """Real-time frame analysis for live streaming."""

    def __init__(self, court_boundary: dict):
        self.court = CourtBoundary(**court_boundary)
        self.pose = mp.solutions.pose.Pose(...)
        self.shot_history = []
        self.foot_positions = []
        self.current_rally_id = 0

    def process_frame(self, frame_data: bytes, timestamp: float) -> dict:
        """Process a single frame and return results."""
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)

        # Run pose detection
        results = self.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Detect shot if any
        shot = self._detect_shot(results, timestamp)

        # Track foot position
        position = self._track_position(results)

        return {
            "shot": shot,
            "position": position,
            "stats": self._get_current_stats()
        }

    def get_final_report(self) -> dict:
        """Generate final report when stream ends."""
        return {
            "summary": {...},
            "shot_distribution": {...},
            "rallies": [...],
            "heatmap_data": self.foot_positions
        }
```

### New WebSocket Handler: `api/websocket/stream_handler.py`

```python
class StreamConnectionManager:
    """Manage live streaming WebSocket connections."""

    active_sessions: Dict[int, StreamAnalyzer] = {}
    connections: Dict[int, List[WebSocket]] = {}

    async def handle_stream(self, websocket: WebSocket, session_id: int):
        """Handle incoming stream frames."""
        analyzer = self.active_sessions[session_id]

        while True:
            message = await websocket.receive_json()

            if message["type"] == "frame":
                # Decode and process frame
                frame_data = base64.b64decode(message["data"])
                results = analyzer.process_frame(frame_data, message["timestamp"])

                # Broadcast results to all viewers
                await self.broadcast_results(session_id, results)

                # Optionally save frame if recording
                if analyzer.is_recording:
                    await self.save_frame(session_id, frame_data)

            elif message["type"] == "end_stream":
                report = analyzer.get_final_report()
                await self.end_session(session_id, report)
                break
```

### New API Endpoints for Streaming

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/stream/create` | Create new stream session |
| POST | `/api/v1/stream/{id}/setup-court` | Set court boundary |
| POST | `/api/v1/stream/{id}/start` | Start streaming |
| POST | `/api/v1/stream/{id}/end` | End stream, get results |
| GET | `/api/v1/stream/{id}/status` | Get current stats |
| POST | `/api/v1/stream/{id}/recording/start` | Start recording |
| POST | `/api/v1/stream/{id}/recording/stop` | Stop recording |

### Frontend Components

**New View: `LiveStreamView.vue`**
```
┌─────────────────────────────────────────────────────────┐
│  Live Analysis                              [Recording] │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐  ┌────────────────────────┐ │
│ │                         │  │ Current Rally: 3       │ │
│ │   Camera Preview        │  │ Shots: 15              │ │
│ │   (with court overlay)  │  │                        │ │
│ │                         │  │ Last Shot: SMASH       │ │
│ │                         │  │ Confidence: 92%        │ │
│ └─────────────────────────┘  │                        │ │
│                              │ ┌────────────────────┐ │ │
│ ┌─────────────────────────┐  │ │   Live Heatmap     │ │ │
│ │ Shot Distribution       │  │ │   (updates live)   │ │ │
│ │ [==smash===][clear]     │  │ │                    │ │ │
│ │ [drop][net]             │  │ └────────────────────┘ │ │
│ └─────────────────────────┘  └────────────────────────┘ │
│                                                         │
│ [End Session]                                           │
└─────────────────────────────────────────────────────────┘
```

**Components:**
- `CameraCapture.vue` - Access camera, capture frames
- `LiveStats.vue` - Real-time shot stats
- `LiveHeatmap.vue` - Heatmap updating in real-time
- `StreamControls.vue` - Start/stop/record controls

### Camera Capture Implementation

**User-Selectable Frame Rate:**
```
┌─────────────────────────────────────┐
│ Stream Quality                      │
│ ┌─────────────────────────────────┐ │
│ │ ○ Low (5 FPS) - Slow connection │ │
│ │ ● Medium (10 FPS) - Recommended │ │
│ │ ○ High (15 FPS) - Fast analysis │ │
│ │ ○ Max (30 FPS) - Best accuracy  │ │
│ └─────────────────────────────────┘ │
│ Estimated bandwidth: ~1 MB/s        │
└─────────────────────────────────────┘
```

```javascript
// CameraCapture.vue
const FPS_OPTIONS = {
  low: { fps: 5, quality: 0.6, label: 'Low (5 FPS)' },
  medium: { fps: 10, quality: 0.7, label: 'Medium (10 FPS)' },
  high: { fps: 15, quality: 0.8, label: 'High (15 FPS)' },
  max: { fps: 30, quality: 0.85, label: 'Max (30 FPS)' }
}

const selectedFps = ref('medium')

async function startCapture() {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 1280, height: 720, facingMode: 'environment' }
  })

  videoElement.srcObject = stream
  ws = new WebSocket(`ws://server/ws/stream/${sessionId}`)

  const { fps, quality } = FPS_OPTIONS[selectedFps.value]
  const interval = 1000 / fps

  frameInterval = setInterval(() => {
    const canvas = captureFrame(videoElement)
    const jpegData = canvas.toDataURL('image/jpeg', quality)

    ws.send(JSON.stringify({
      type: 'frame',
      timestamp: Date.now() / 1000,
      data: jpegData.split(',')[1]
    }))
  }, interval)
}
```

---

## Implementation Phases (Parallel Approach)

> **Design Principle**: Build shared components first to ensure S3 and streaming don't conflict.

### Phase 1: Shared Infrastructure
*Foundation used by both S3 uploads and live streaming*

1. **Storage Abstraction Layer** (`api/services/storage_service.py`)
   - Interface for local/S3 storage operations
   - Unified API: `save()`, `load()`, `get_url()`, `delete()`
   - Auto-switch based on config (local dev vs AWS prod)

2. **Database Schema Updates**
   - Add `storage_type`, `s3_video_key`, `s3_output_prefix` to Job model
   - Create `StreamSession` model
   - Migration script for existing data

3. **Configuration Updates**
   - S3 settings (bucket, region, CloudFront)
   - Streaming settings (max FPS, buffer size)
   - Environment-based switching

### Phase 2A: S3 Storage (parallel with 2B)
1. Implement S3Service (pre-signed URLs, multipart)
2. Create upload endpoints (`/upload/request`, `/upload/confirm`)
3. Modify AnalyzerService to use storage abstraction
4. Frontend S3Uploader component with progress
5. Test with LocalStack locally

### Phase 2B: Live Streaming Backend (parallel with 2A)
1. Extract `FrameAnalyzer` from `CourtBoundedAnalyzer`
   - Shared pose detection logic
   - Works for both video frames and live frames
2. Implement `StreamAnalyzer` using `FrameAnalyzer`
3. Create WebSocket stream handler
4. Stream session API endpoints
5. Recording to storage (local or S3)

### Phase 3: Frontend Integration
1. **S3 Upload**: S3Uploader component, progress tracking
2. **Live Stream**: CameraCapture, LiveStreamView
3. **Shared**: LiveHeatmap (used in both results & streaming)
4. **Settings**: Frame rate selector, quality options

### Phase 4: Testing & Optimization
1. End-to-end tests for both flows
2. LocalStack for S3 testing locally
3. Connection quality detection → auto frame rate
4. Mobile browser testing (camera permissions)
5. Load testing for concurrent streams

---

## Shared Components (Prevents Conflicts)

```
                    ┌─────────────────────────┐
                    │   StorageService        │
                    │   (abstraction layer)   │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
       ┌────────────┐   ┌────────────┐   ┌────────────┐
       │ LocalStore │   │  S3Store   │   │ TempStore  │
       │ (dev mode) │   │ (AWS prod) │   │ (streams)  │
       └────────────┘   └────────────┘   └────────────┘


                    ┌─────────────────────────┐
                    │    FrameAnalyzer        │
                    │  (core pose detection)  │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                                   ▼
       ┌────────────────┐                 ┌────────────────┐
       │ VideoAnalyzer  │                 │ StreamAnalyzer │
       │ (batch files)  │                 │ (real-time)    │
       └────────────────┘                 └────────────────┘
```

**Why This Helps:**
- `StorageService`: Same code works locally and on AWS
- `FrameAnalyzer`: Shared detection logic, no duplication
- Changes to pose detection benefit both video and streaming

---

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| **Shared Infrastructure** | |
| `api/services/storage_service.py` | Storage abstraction (local/S3) |
| `api/services/frame_analyzer.py` | Core pose detection (shared) |
| **S3 Storage** | |
| `api/services/s3_service.py` | S3-specific operations |
| `api/routers/upload.py` | Pre-signed URL endpoints |
| `frontend/src/components/S3Uploader.vue` | Direct S3 upload with progress |
| **Live Streaming** | |
| `api/services/stream_service.py` | Real-time stream analyzer |
| `api/routers/stream.py` | Stream session endpoints |
| `api/websocket/stream_handler.py` | WebSocket frame handler |
| `api/db_models/stream_session.py` | Stream session model |
| `frontend/src/components/CameraCapture.vue` | Camera access + FPS selector |
| `frontend/src/components/LiveStats.vue` | Real-time shot stats |
| `frontend/src/components/LiveHeatmap.vue` | Live updating heatmap |
| `frontend/src/views/LiveStreamView.vue` | Streaming page |

### Modified Files
| File | Changes |
|------|---------|
| `api/config.py` | Add S3 settings |
| `api/services/analyzer_service.py` | S3 input/output support |
| `api/services/job_manager.py` | S3 download/upload |
| `api/db_models/job.py` | Add S3 fields |
| `api/main.py` | Add new routers |
| `requirements-web.txt` | Add boto3 |
| `frontend/src/router/index.js` | Add stream route |
| `frontend/src/stores/jobs.js` | Add stream store |

---

## AWS Services Used

| Service | Purpose |
|---------|---------|
| **S3** | Video storage, analysis outputs |
| **CloudFront** | CDN for fast video/image delivery |
| **EC2/ECS** | Run FastAPI backend |
| **RDS** | PostgreSQL database (instead of SQLite) |
| **ElastiCache** | Redis for WebSocket pub/sub (scaling) |
| **API Gateway** | WebSocket management (optional) |

---

## Verification

1. **S3 Upload**: Upload large video → Progress shown → File in S3 → Analysis works
2. **S3 Download**: View results → Videos/heatmaps load from S3/CloudFront
3. **Live Stream**: Open camera → Select court → Start stream → See live shots → End → View report
4. **Recording**: Enable recording → Stream → End → Playback saved video
5. **Mobile**: Test camera capture on phone browser

---

## Environment Variables (Production)

```bash
# S3
S3_BUCKET=badminton-analyzer-prod
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
CLOUDFRONT_DOMAIN=d1234.cloudfront.net

# Database
DATABASE_URL=postgresql://user:pass@rds-host:5432/badminton

# Redis (for WebSocket scaling)
REDIS_URL=redis://elasticache-host:6379
```
