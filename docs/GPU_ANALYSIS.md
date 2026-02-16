# GPU & Infrastructure Analysis

**Date**: February 2026
**Status**: Benchmarked, not yet integrated into production

---

## 1. Current Production Setup

| Component | Detail |
|---|---|
| **Instance** | ECS on EC2 (t3.medium-equivalent, 2 vCPU, 4GB RAM) |
| **Docker image** | `python:3.11-slim` (CPU only, no torch) |
| **Analysis pipeline** | Pose detection only (MediaPipe) — no shuttle tracking |
| **Shuttle tracking** | Auto-disabled — `ShuttleService.is_available()` returns `False` (no torch in container) |
| **Transcode** | Balanced preset: max 1080p, H.264, CRF 23 |
| **Processing** | `processing_width=640`, `model_complexity=1`, every frame |
| **Upload limit** | 100MB (reduced from 500MB to prevent OOM) |
| **Cost** | ~$45/month |

### How Shuttle Tracking Auto-Detection Works

```python
# api/services/shuttle_service.py
class ShuttleService:
    @staticmethod
    def is_available() -> bool:
        try:
            import torch                    # Fails in prod Docker (no torch)
            from shuttle_tracking.shuttle_tracker import DEFAULT_WEIGHTS_PATH
            return DEFAULT_WEIGHTS_PATH.exists()  # weights/track.pt (45MB)
        except ImportError:
            return False
```

- **Production**: `import torch` fails → no shuttle tracking → pose-only at ~27 FPS
- **Local Mac** (Apple Silicon): torch + MPS available → shuttle tracking enabled → ~10 FPS
- **No config flag** — purely environment-based detection

---

## 2. Benchmark Results

### 2.1 Test Environment

| Setup | Instance | GPU | Notes |
|---|---|---|---|
| **Production ECS** | t3-equivalent, 2 vCPU | None | Docker, pose-only |
| **Local Mac** | Apple Silicon (M-series) | MPS (Metal) | Full pipeline with shuttle |
| **AWS GPU** | g4dn.xlarge, 4 vCPU, 16GB RAM | Tesla T4 (15GB VRAM) | Benchmark instance |

### 2.2 Component-Level Benchmarks (720p, 300 frames)

| Component | CPU | GPU (Tesla T4) | Speedup |
|---|---|---|---|
| MediaPipe Pose only | 20.2 FPS | N/A (CPU-only library) | — |
| TrackNetV2 only | 0.5 FPS | 7.9 FPS | **17x** |
| Full Pipeline (Pose + Shuttle) | 0.4 FPS | 8.2 FPS | **20x** |

**Key insight**: TrackNetV2 is the bottleneck. MediaPipe has no GPU support in Python — always runs on CPU at ~20 FPS.

### 2.3 Production-Realistic Benchmarks (720p@30fps, 1800 frames on g4dn.xlarge)

| Test | Config | FPS | 5-min video time |
|---|---|---|---|
| **Test 1**: CPU pose-only | No shuttle, processing_width=640, model=1 | **38.1 FPS** | 3.9 min |
| **Test 2**: GPU pose + shuttle (every frame) | CUDA shuttle, processing_width=640, model=1 | **9.4 FPS** | 16.0 min |
| **Test 3**: GPU pose + shuttle (skip every 2nd) | Same as Test 2, process_every_n=2 | **18.6 FPS** | 8.1 min |

### 2.4 Real-World Production vs Local (848x478@30fps, 986 frames, 33s video)

| Environment | Shuttle Tracking | Device | Detection FPS | Total Time |
|---|---|---|---|---|
| **Production ECS** | OFF (no torch) | CPU | **~27 FPS** | ~44s |
| **Local Mac** | ON | MPS (Metal) | **~10 FPS** | ~100s |
| **AWS GPU** (g4dn.xlarge) | ON | CUDA (Tesla T4) | **~9.4 FPS** | ~105s |
| **AWS CPU** (g4dn.xlarge) | ON | CPU | **~0.4 FPS** | ~41 min |

### 2.5 Full 60-Second Analysis (4K@60fps, 3600 frames, GPU)

| Phase | Time | Notes |
|---|---|---|
| Phase 1: Detection | 7.5 min | Pose (CPU) + Shuttle (CUDA) on every frame |
| Phase 2: Classification | <1 sec | 41 shots, 5 rallies |
| Phase 3: Annotation | 5.0 min | Writing 4K annotated video (289 MB) |
| **Total** | **12.6 min** | **4.8 effective FPS** |

---

## 3. Key Findings

1. **Production is already fast without shuttle tracking** — 27 FPS pose-only is faster than real-time. No GPU needed for current feature set.

2. **GPU only matters if shuttle tracking is enabled** — TrackNetV2 is 0.4 FPS on CPU vs 8-9 FPS on GPU. Without it, pose detection alone is 20-38 FPS on CPU.

3. **Mac MPS ≈ Tesla T4 for this workload** — Both achieve ~10 FPS for combined pose + shuttle. MPS is surprisingly competitive.

4. **4K@60fps is expensive** — Doubles the frame count and increases per-frame cost. Transcoding to 720p@30fps before analysis is critical for any GPU pipeline.

5. **Phase 3 (annotation) is 40% of total time at 4K** — Resolution reduction helps annotation phase too, not just detection.

6. **Frame skipping (process_every_n=2) nearly doubles throughput** — 9.4 FPS → 18.6 FPS with minimal quality loss for shot classification.

---

## 4. Path to Real-Time (30 FPS) — Not Yet Implemented

### 4.1 Per-Frame Bottleneck Breakdown (720p, current T4 setup)

| Component | Time/frame | FPS | Runs on | GPU-accelerable? |
|---|---|---|---|---|
| MediaPipe Pose | ~50ms | ~20 FPS | CPU only | No (Python API limitation) |
| TrackNetV2 (FP32) | ~125ms | ~8 FPS | GPU (Tesla T4) | Already on GPU |
| **Combined (sequential)** | **~106ms** | **~9.4 FPS** | Mixed | — |

Two independent bottlenecks: MediaPipe is CPU-bound, TrackNetV2 is GPU-bound. Currently they run sequentially — parallelizing them is the first big win.

### 4.2 Software Optimizations (same Tesla T4)

| Step | TrackNet FPS | Combined FPS | Effort | Notes |
|---|---|---|---|---|
| Baseline (FP32, sequential) | ~8 | ~9.4 | — | Current state |
| **FP16 half precision** | ~16 | ~14 | Trivial | `model.half()` — T4 has Tensor Cores for FP16 (65 TFLOPS vs 8.1 FP32) |
| **+ Async pipeline** (pose ∥ shuttle) | ~16 | **~18-20** | Low | Threading: pose on CPU while TrackNet on GPU simultaneously |
| **+ TensorRT export** | ~30-40 | **~25-30** | Moderate | Export `.pt` → `.engine`, ~1.5x over FP16 |
| **+ Frame skip (process_every_n=2)** | ~30-40 | **~50-60 effective** | Low | Already supported in code |

### 4.3 GPU Upgrade Options

If software optimizations on T4 aren't sufficient:

| GPU | Instance | TFLOPS (FP16) | Est. TrackNet FPS | Est. Combined FPS | Spot $/hr |
|---|---|---|---|---|---|
| Tesla T4 (current) | g4dn.xlarge | 65 | 8 (FP32) / ~16 (FP16) | ~9.4 / ~14 | $0.25 |
| **A10G** | g5.xlarge | 125 | ~18 (FP32) / ~35 (FP16) | ~25-30 | ~$0.50 |
| **L4** | g6.xlarge | 121 | ~20 (FP32) / ~40 (FP16) | ~25-30 | ~$0.45 |
| A100 (40GB) | p4d.xlarge | 312 | ~40 (FP32) / ~80 (FP16) | ~40+ | ~$4+ (overkill) |

**A10G or L4 with FP16 + TensorRT would comfortably hit 30+ FPS** for TrackNetV2 alone.

### 4.4 The MediaPipe Ceiling

Even with infinitely fast TrackNetV2, MediaPipe caps combined throughput at ~20 FPS (CPU-only Python API). Solutions:

| Approach | Expected Pose FPS | Effort | Trade-offs |
|---|---|---|---|
| **Frame skip pose (every 2nd, interpolate)** | ~40 effective | Low | Minor accuracy loss between frames |
| **RTMPose / YOLO-Pose** (GPU-native) | 60-100+ on T4 | Medium | Replace MediaPipe entirely; different landmark format |
| MediaPipe C++ API with GPU | ~40-50 | High | Rewrite detection loop in C++ |
| **Async pipeline** (pose ∥ shuttle) | ~20 (hidden) | Low | Doesn't increase pose FPS but overlaps with GPU work |

**Recommended**: Async pipeline first (hides MediaPipe latency behind GPU work). If pose becomes the bottleneck after TrackNet is optimized, switch to RTMPose.

### 4.5 Recommended Roadmap to 30 FPS

```
Current state
  9.4 FPS (FP32, T4, sequential, every frame)
      │
      ├─ Step 1: FP16 TrackNetV2              [Trivial — 1 line]
      │    ~14 FPS
      │
      ├─ Step 2: Async pipeline               [Low — threading]
      │    ~18-20 FPS  (pose on CPU ∥ shuttle on GPU)
      │
      ├─ Step 3a: TensorRT export             [Moderate — model export]
      │    ~25-30 FPS  ✅ Real-time on T4
      │
      └─ OR Step 3b: Upgrade to A10G/L4       [No code change, 2x cost]
           ~25-30 FPS  ✅ Real-time with FP16 alone
```

**Steps 1+2 are nearly free** and get to ~20 FPS. Then either TensorRT (free, moderate effort) or a better GPU (easy, ~$0.45/hr) closes the gap to 30 FPS.

If 30 FPS still isn't enough after Step 3:
- Add frame skipping (`process_every_n=2`) → **60 FPS effective**
- Replace MediaPipe with RTMPose → removes CPU ceiling entirely

---

## 5. Proposed GPU Architecture (Not Yet Built)

```
                    ┌──────────────────────────┐
                    │       ALB / Nginx         │
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │   CPU ECS (always-on)     │
                    │   - API server            │
                    │   - Challenge processing  │
                    │   - Job queue manager     │
                    │   - Pose-only analysis    │
                    └──────────┬───────────────┘
                               │ SQS
                    ┌──────────▼───────────────┐
                    │   GPU (on-demand)         │
                    │   AWS Batch / g4dn.xlarge │
                    │   - Shuttle tracking      │
                    │   - Full pipeline         │
                    │   - Scale to zero         │
                    └──────────────────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │   S3 (results storage)    │
                    └──────────────────────────┘
```

### Communication Flow
1. User uploads video → CPU ECS receives, stores in S3
2. CPU ECS puts message on SQS queue
3. AWS Batch picks up job, spins up g4dn.xlarge spot instance
4. GPU processes video (pose + shuttle), writes results to S3
5. CPU ECS polls for completion, notifies user

### Cost Estimates

| Scenario | Monthly Cost |
|---|---|
| Current (CPU only, no shuttle) | ~$45 |
| + GPU on-demand (spot @ $0.25/hr) | ~$45 base + ~$0.08/video |
| 100 videos/month | ~$53 total |
| 500 videos/month | ~$85 total |

---

## 6. AWS GPU Setup Notes

| Item | Detail |
|---|---|
| **Instance** | g4dn.xlarge (4 vCPU, 16GB RAM, Tesla T4 15GB VRAM) |
| **Region** | ap-south-1 (Mumbai) |
| **Spot price** | ~$0.25/hr |
| **On-demand price** | ~$0.53/hr |
| **AMI** | `ami-0a5c5e08e5bc85ede` (Deep Learning PyTorch 2.9, Ubuntu 24.04) |
| **VPC/SG** | vpc-0d7171cdfeedeadf2 / sg-0bae4d0dca70bbb36 |
| **SSH key** | `badminton-analyzer-key.pem` |
| **GPU quota codes** | L-3819A6DF (spot), L-DB2E81BA (on-demand) |
| **Quota default** | 0 vCPUs — must request increase via Service Quotas console |
| **Spot availability** | Can be unavailable in some AZs; try all 3 (a, b, c) |

### Docker Changes Needed for GPU
- Current: `python:3.11-slim` (CPU only)
- GPU: `nvidia/cuda:12.1.1-runtime-ubuntu22.04` + `pip install torch --index-url https://download.pytorch.org/whl/cu121`
- ShuttleTracker auto-detects CUDA — no code changes needed

---

## 7. Decision Summary

### Current State
Production runs **pose-only at ~27 FPS** (faster than real-time). No GPU needed for current feature set. Shuttle tracking is auto-disabled because Docker image has no torch.

### When GPU Is Needed
Only when shuttle tracking becomes a production feature. Without it, CPU is more than sufficient.

### Roadmap to 30 FPS with Shuttle Tracking

| Phase | What | FPS | Cost | Effort |
|---|---|---|---|---|
| **Now** | CPU pose-only (no shuttle) | 27 | $45/mo | Done |
| **Phase 1** | Add GPU + FP16 + async pipeline | ~20 | +$0.08/video | Low |
| **Phase 2** | + TensorRT OR upgrade to A10G/L4 | **~30** | +$0.08-0.15/video | Moderate |
| **Phase 3** | + RTMPose (replace MediaPipe) | **~50+** | Same | Medium |

### Key Decisions
1. **Keep production as-is** — 27 FPS pose-only is excellent
2. **When enabling shuttle tracking**: Start with T4 + FP16 + async (cheapest, gets to ~20 FPS)
3. **If 30 FPS needed**: TensorRT on T4 (free) or upgrade to A10G/L4 (~2x cost)
4. **If real-time streaming needed**: Replace MediaPipe with RTMPose to remove CPU ceiling
