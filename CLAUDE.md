# CLAUDE.md

## Project Overview

**PushUp Pro / Badminton Analyzer** — A full-stack AI-powered fitness and sports analysis platform. Users can upload or livestream video for real-time pose detection, shot classification, and movement coaching. Features include badminton analysis, fitness challenges (pushup, squat, plank), and MoveMatch (mimic dance moves from reference videos).

**Live at:** `https://badminton.neymo.ai`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn (Python 3.11) |
| Frontend | Vue 3 + Vite 5 + Pinia |
| Database | SQLite (dev) / MySQL via pymysql (prod) |
| ORM | SQLAlchemy 2.0 (declarative_base) |
| Auth | JWT (python-jose), bcrypt (passlib), Google OAuth, email OTP |
| Storage | Local filesystem (dev) / AWS S3 + CloudFront (prod) |
| AI/ML | MediaPipe (pose), TrackNetV2/PyTorch (shuttle), YOLOv8 (detection), Vosk (voice) |
| Infra | Docker, AWS ECS, ECR, EC2, Secrets Manager, Route 53 |
| Observability | Datadog APM (ddtrace), DogStatsD, correlation IDs |

## Running Locally

### Backend
```bash
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
API docs: `http://localhost:8000/docs` | Health: `http://localhost:8000/health`

### Frontend
```bash
cd frontend && npm install && npm run dev
```
Dev server: `https://localhost:5173` (HTTPS required for camera API)

Vite proxies `/api` → `http://localhost:8000` and `/ws` → `ws://localhost:8000`.

### Tests
```bash
pytest tests/ -v
```

## Project Structure

```
api/                          # FastAPI backend
  main.py                     # App entrypoint, WebSocket routes, lifespan
  config.py                   # pydantic-settings (reads .env)
  database.py                 # SQLAlchemy engine, init_db(), manual migrations
  routers/                    # REST endpoints (auth, upload, analysis, stream, admin, tuning)
  services/                   # Business logic (analyzer, shot classifier, shuttle)
  features/                   # Feature plugins (challenges, mimic, workout)
    registry.py               # BaseFeature plugin system, install_routers()
    mimic/                    # MoveMatch feature
      routers/mimic.py        # REST + compare endpoints
      services/               # video_comparator, audio_sync, pose_similarity, reference_processor
      db_models/mimic.py      # MimicChallenge, MimicSession, MimicRecord
    challenges/               # Fitness challenges (pushup, squat, plank)
    workout/                  # Workout tracking
  core/                       # Shared infra (streaming, pose_detector, metrics, correlation)
  db_models/                  # Shared DB models (user, tuning, feature_access)
frontend/                     # Vue 3 SPA
  src/views/                  # Page components
  src/stores/                 # Pinia stores (auth, mimic, etc.)
  src/api/client.js           # Axios instance
shuttle_tracking/             # TrackNetV2 wrapper (shuttle_tracker.py)
v2_court_bounded_analyzer.py  # Main analyzer (~2700 lines), 3-phase pipeline
weights/                      # Model weights (gitignored)
tests/                        # Pytest suite
scripts/                      # Utility scripts
docs/                         # Internal docs
```

## Key Architectural Patterns

### Feature Plugin System
Each feature implements `BaseFeature` in `api/features/registry.py` and registers its own routers. Features are installed at startup via `feature_registry.install_routers(app)`. Per-user feature gating via `users.enabled_features` JSON column.

### Database Migrations
**No Alembic.** All schema changes are manual `ALTER TABLE` in `api/database.py:init_db()`, which runs on every startup. To add a column: write a `_migrate_*()` function there.

### Video Analysis Pipeline (Badminton)
3-phase approach in `v2_court_bounded_analyzer.py`:
1. **Detection** — pose + shuttle detection every frame
2. **Classification** — ShotClassifier post-processing (hit-centric sliding window)
3. **Annotation** — video writing with overlays

### WebSocket Protocols
- `/ws/stream/{session_id}` — live badminton analysis
- `/ws/challenge/{session_id}` — fitness challenges (pushup, squat, plank)
- `/ws/mimic/{session_id}` — MoveMatch live sessions
- Frame dropping for hold-based challenges; sequential for rep-based

### MoveMatch (Mimic) Upload-to-Compare Flow
1. User uploads video → `POST /challenges/{id}/compare` → creates session, kicks off `compare_video()` in daemon thread
2. Background thread: audio offset alignment → pose extraction → frame-by-frame scoring → side-by-side video generation
3. Frontend polls `GET /sessions/{id}` until `status === 'ended'` or `'audio_mismatch'`

## Common Gotchas

- **`api/services/__init__.py` imports everything** — can't import individual services in isolation without pulling in bcrypt etc. Use `importlib.util.spec_from_file_location` for isolated testing.
- **MediaPipe landmarks are normalized to cropped court region**, not full frame. `_last_transform` maps back.
- **`pose_landmarks` objects are not serializable** — stored in `raw_frame_data` only for in-memory annotation pass.
- **Velocity thresholds are time-based** (per second), FPS-independent. Always pass `effective_fps=video_fps` when testing outside the analyzer pipeline.
- **The `turbo` preset** was removed from `SPEED_PRESETS` but still exists in `TRANSCODE_SETTINGS` and the UI.
- **Shuttle tracking weights** at `weights/track.pt` (~45MB, gitignored). ShuttleTracker auto-detects CUDA (`device="auto"`).

## Configuration

All settings in `api/config.py` via pydantic-settings (reads `.env`). Key vars:

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `sqlite:///./badminton_analyzer.db` | MySQL/PG in prod |
| `JWT_SECRET_KEY` | `dev-secret-key-change-in-production` | **Must change in prod** |
| `USE_S3` | `True` | Set `False` for local-only storage |
| `EMAIL_PROVIDER` | `console` | `console` / `smtp` / `ses` |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated |
| `MAX_UPLOAD_SIZE_MB` | `100` | Prevents OOM |
| `DD_TRACE_ENABLED` | — | Set `1` for Datadog APM |

## Deployment

```bash
./deploy.sh              # Build Docker, push ECR, update ECS
cd frontend && ./deploy.sh  # Build Vue, SCP to EC2/Nginx
```

Production: Docker (python:3.11-slim) on AWS ECS, Nginx reverse proxy on EC2, API on port 8002.
