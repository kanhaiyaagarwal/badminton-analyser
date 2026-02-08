"""
Tuning API Router - Endpoints for shot detection threshold tuning.

Provides:
- CRUD for tuning presets
- Video tuning sessions with frame data caching
- Fast re-classification without re-running pose detection
- Activity schema endpoints for dynamic UI generation
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import get_settings
from ..db_models.tuning import TuningPreset, ActivityThresholdSchema, TuningSession
from ..db_models.job import Job
from ..db_models.user import User
from ..models.tuning import (
    TuningPresetCreate,
    TuningPresetUpdate,
    TuningPresetResponse,
    TuningPresetListResponse,
    TuningSessionCreate,
    TuningSessionResponse,
    ReclassifyRequest,
    ReclassifyResponse,
    FrameDataExport,
    get_default_badminton_thresholds,
    get_badminton_activity_schema,
)
from ..services.tuning_service import (
    TuningService,
    load_frame_data,
    enrich_frame_data,
    reclassify_shots,
    extract_velocity_thresholds,
)
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tuning", tags=["tuning"])


# ============================================================================
# Helper functions
# ============================================================================

def _load_job_frame_data(job) -> Optional[dict]:
    """Load frame data for a job from local storage or S3.

    Returns the frame data dict or None if not found.
    Automatically enriches old-format data that's missing velocity/classification fields.
    """
    frame_data = None
    settings = get_settings()

    # Try loading from local output directory first
    output_dir = settings.output_path / str(job.user_id) / str(job.id)

    if output_dir.exists():
        frame_data_files = list(output_dir.glob("frame_data_*.json"))
        if frame_data_files:
            frame_data = load_frame_data(str(frame_data_files[0]))
            if frame_data:
                logger.info(f"Loaded frame data from local: {frame_data_files[0]}")
                return enrich_frame_data(frame_data)

    # If not found locally, try S3
    from ..services.storage_service import get_storage_service
    storage = get_storage_service()

    if storage.is_s3():
        try:
            # The file is stored as: analysis_output/{job_id}/frame_data_*.json
            s3_prefix = f"analysis_output/{job.id}/"

            # Try common patterns first
            video_stem = job.video_filename.rsplit('.', 1)[0] if job.video_filename else "video"
            patterns = [
                f"frame_data_{video_stem}.json",
                "frame_data.json"
            ]

            for pattern in patterns:
                test_key = f"{s3_prefix}{pattern}"
                try:
                    data = storage.outputs.load(test_key)
                    if data:
                        frame_data = json.loads(data.decode('utf-8'))
                        logger.info(f"Loaded frame data from S3: {test_key}")
                        return enrich_frame_data(frame_data)
                except Exception:
                    continue

            # If still not found, list the bucket to find frame_data files
            import boto3
            s3_client = boto3.client('s3')
            bucket = storage.outputs.bucket
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=s3_prefix)

            for obj in response.get('Contents', []):
                if 'frame_data' in obj['Key'] and obj['Key'].endswith('.json'):
                    data = storage.outputs.load(obj['Key'])
                    frame_data = json.loads(data.decode('utf-8'))
                    logger.info(f"Loaded frame data from S3: {obj['Key']}")
                    return enrich_frame_data(frame_data)

        except Exception as e:
            logger.warning(f"Failed to load frame data from S3: {e}")

    return None


# ============================================================================
# Admin check dependency
# ============================================================================

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin user for tuning endpoints."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for tuning"
        )
    return current_user


# ============================================================================
# Activity Schema Endpoints
# ============================================================================

@router.get("/schemas")
async def list_activity_schemas(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all available activity threshold schemas."""
    schemas = db.query(ActivityThresholdSchema).all()

    # If no schemas in DB, return default badminton schema
    if not schemas:
        return [get_badminton_activity_schema()]

    return [
        {
            "activity_type": s.activity_type,
            "display_name": s.display_name,
            "description": s.description,
            "schema": s.schema
        }
        for s in schemas
    ]


@router.get("/schemas/{activity_type}")
async def get_activity_schema(
    activity_type: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get threshold schema for a specific activity type."""
    schema = db.query(ActivityThresholdSchema).filter(
        ActivityThresholdSchema.activity_type == activity_type
    ).first()

    if not schema:
        # Return default badminton schema if not in DB
        if activity_type == "badminton":
            return get_badminton_activity_schema()
        raise HTTPException(status_code=404, detail=f"Schema not found for activity: {activity_type}")

    return {
        "activity_type": schema.activity_type,
        "display_name": schema.display_name,
        "description": schema.description,
        "schema": schema.schema
    }


# ============================================================================
# Preset CRUD Endpoints
# ============================================================================

@router.get("/presets", response_model=TuningPresetListResponse)
async def list_presets(
    activity_type: str = "badminton",
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all tuning presets for an activity type."""
    presets = db.query(TuningPreset).filter(
        TuningPreset.activity_type == activity_type
    ).order_by(TuningPreset.is_default.desc(), TuningPreset.name).all()

    # Find active preset
    active_preset = next((p for p in presets if p.is_active), None)

    return TuningPresetListResponse(
        presets=[TuningPresetResponse.model_validate(p) for p in presets],
        active_preset_id=active_preset.id if active_preset else None
    )


@router.get("/presets/active", response_model=Optional[TuningPresetResponse])
async def get_active_preset(
    activity_type: str = "badminton",
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get the currently active preset for an activity type."""
    preset = db.query(TuningPreset).filter(
        TuningPreset.activity_type == activity_type,
        TuningPreset.is_active == True
    ).first()

    if not preset:
        # Return default thresholds if no active preset
        return None

    return TuningPresetResponse.model_validate(preset)


@router.get("/presets/defaults")
async def get_default_thresholds(
    activity_type: str = "badminton",
    current_user: User = Depends(get_admin_user)
):
    """Get default thresholds for an activity type."""
    if activity_type == "badminton":
        return get_default_badminton_thresholds()
    raise HTTPException(status_code=404, detail=f"No defaults for activity: {activity_type}")


@router.get("/presets/{preset_id}", response_model=TuningPresetResponse)
async def get_preset(
    preset_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific preset by ID."""
    preset = db.query(TuningPreset).filter(TuningPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return TuningPresetResponse.model_validate(preset)


@router.post("/presets", response_model=TuningPresetResponse, status_code=status.HTTP_201_CREATED)
async def create_preset(
    preset_data: TuningPresetCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new tuning preset."""
    # Check for duplicate name
    existing = db.query(TuningPreset).filter(
        TuningPreset.name == preset_data.name,
        TuningPreset.activity_type == preset_data.activity_type
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Preset with name '{preset_data.name}' already exists"
        )

    preset = TuningPreset(
        name=preset_data.name,
        description=preset_data.description,
        activity_type=preset_data.activity_type,
        thresholds=preset_data.thresholds,
        is_active=False,
        is_default=False,
        created_by=current_user.id
    )

    db.add(preset)
    db.commit()
    db.refresh(preset)

    logger.info(f"Created tuning preset: {preset.name} (id={preset.id})")
    return TuningPresetResponse.model_validate(preset)


@router.put("/presets/{preset_id}", response_model=TuningPresetResponse)
async def update_preset(
    preset_id: int,
    preset_data: TuningPresetUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update an existing preset."""
    preset = db.query(TuningPreset).filter(TuningPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    # Don't allow modifying system default
    if preset.is_default and preset_data.thresholds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify system default preset thresholds"
        )

    # Update fields
    if preset_data.name is not None:
        # Check for duplicate name
        existing = db.query(TuningPreset).filter(
            TuningPreset.name == preset_data.name,
            TuningPreset.activity_type == preset.activity_type,
            TuningPreset.id != preset_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Preset with name '{preset_data.name}' already exists"
            )
        preset.name = preset_data.name

    if preset_data.description is not None:
        preset.description = preset_data.description

    if preset_data.thresholds is not None:
        preset.thresholds = preset_data.thresholds

    db.commit()
    db.refresh(preset)

    logger.info(f"Updated tuning preset: {preset.name} (id={preset.id})")
    return TuningPresetResponse.model_validate(preset)


@router.post("/presets/{preset_id}/activate", response_model=TuningPresetResponse)
async def activate_preset(
    preset_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Set a preset as the active preset for its activity type."""
    preset = db.query(TuningPreset).filter(TuningPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    # Deactivate all other presets for this activity
    db.query(TuningPreset).filter(
        TuningPreset.activity_type == preset.activity_type,
        TuningPreset.id != preset_id
    ).update({"is_active": False})

    preset.is_active = True
    db.commit()
    db.refresh(preset)

    logger.info(f"Activated tuning preset: {preset.name} (id={preset.id})")
    return TuningPresetResponse.model_validate(preset)


@router.delete("/presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(
    preset_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a preset (non-default only)."""
    preset = db.query(TuningPreset).filter(TuningPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    if preset.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system default preset"
        )

    db.delete(preset)
    db.commit()

    logger.info(f"Deleted tuning preset: {preset.name} (id={preset_id})")


# ============================================================================
# Tuning Session Endpoints
# ============================================================================

@router.post("/sessions", response_model=TuningSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_tuning_session(
    session_data: TuningSessionCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new tuning session from an existing job."""
    # Validate job exists and belongs to user or is admin accessible
    job = None
    if session_data.job_id:
        job = db.query(Job).filter(Job.id == session_data.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    session = TuningSession(
        job_id=session_data.job_id,
        user_id=current_user.id,
        name=session_data.name,
        activity_type=session_data.activity_type,
        status="created"
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(f"Created tuning session: id={session.id}, job_id={session.job_id}")
    return TuningSessionResponse.model_validate(session)


@router.get("/sessions", response_model=List[TuningSessionResponse])
async def list_tuning_sessions(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all tuning sessions for the current user."""
    sessions = db.query(TuningSession).filter(
        TuningSession.user_id == current_user.id
    ).order_by(TuningSession.created_at.desc()).all()

    return [TuningSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=TuningSessionResponse)
async def get_tuning_session(
    session_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific tuning session."""
    session = db.query(TuningSession).filter(
        TuningSession.id == session_id,
        TuningSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return TuningSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/analyze")
async def analyze_session(
    session_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Run initial analysis for a tuning session (generates frame data)."""
    session = db.query(TuningSession).filter(
        TuningSession.id == session_id,
        TuningSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no associated job"
        )

    job = db.query(Job).filter(Job.id == session.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Associated job not found")

    # Check if frame data already exists
    if session.frame_data_path and Path(session.frame_data_path).exists():
        return {"status": "ready", "message": "Frame data already exists"}

    # For now, return that this needs to be run via the job
    # In production, this would trigger a background task
    return {
        "status": "pending",
        "message": "Frame data generation needs to be run. Re-run the job with save_frame_data=True"
    }


@router.get("/sessions/{session_id}/frame-data")
async def get_session_frame_data(
    session_id: int,
    offset: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=0, description="Max frames to return. 0 or omit for all frames."),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get frame data for a tuning session.

    Args:
        offset: Starting frame index
        limit: Max frames to return. Pass 0 or omit to get all frames.
    """
    session = db.query(TuningSession).filter(
        TuningSession.id == session_id,
        TuningSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.frame_data_path or not Path(session.frame_data_path).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Frame data not available. Run analysis first."
        )

    # Load frame data
    frame_data = load_frame_data(session.frame_data_path)
    if not frame_data:
        raise HTTPException(status_code=500, detail="Failed to load frame data")

    frames = frame_data.get("frames", [])
    total = len(frames)

    # If limit is None or 0, return all frames from offset
    if limit is None or limit == 0:
        result_frames = frames[offset:]
    else:
        result_frames = frames[offset:offset + limit]

    return {
        "session_id": session_id,
        "video_info": frame_data.get("video_info"),
        "thresholds_used": frame_data.get("thresholds_used"),
        "total_frames": total,
        "offset": offset,
        "limit": limit if limit else total,
        "frames": result_frames
    }


@router.post("/sessions/{session_id}/reclassify")
async def reclassify_session(
    session_id: int,
    request: ReclassifyRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Re-classify shots in a session with new thresholds."""
    session = db.query(TuningSession).filter(
        TuningSession.id == session_id,
        TuningSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.frame_data_path or not Path(session.frame_data_path).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Frame data not available. Run analysis first."
        )

    # Load frame data
    frame_data = load_frame_data(session.frame_data_path)
    if not frame_data:
        raise HTTPException(status_code=500, detail="Failed to load frame data")

    # Re-classify with new thresholds
    results = reclassify_shots(
        frame_data=frame_data,
        new_thresholds=request.velocity_thresholds,
        new_cooldown=request.shot_cooldown_seconds,
        position_thresholds=request.position_thresholds
    )

    # Update session with current thresholds
    session.current_thresholds = {
        "velocity": request.velocity_thresholds,
        "position": request.position_thresholds,
        "cooldown": {"shot_cooldown_seconds": request.shot_cooldown_seconds}
    }
    db.commit()

    return results


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tuning_session(
    session_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a tuning session."""
    session = db.query(TuningSession).filter(
        TuningSession.id == session_id,
        TuningSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    logger.info(f"Deleted tuning session: id={session_id}")


# ============================================================================
# Job-based Tuning Endpoints (alternative to sessions)
# ============================================================================

@router.get("/jobs/{job_id}/frame-data")
async def get_job_frame_data(
    job_id: int,
    offset: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=0, description="Max frames to return. 0 or omit for all frames."),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get frame data directly from a job's output directory.

    Args:
        offset: Starting frame index
        limit: Max frames to return. Pass 0 or omit to get all frames.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    frame_data = _load_job_frame_data(job)

    if not frame_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Frame data not available. Re-run analysis with 'Enable tuning data' checked."
        )

    frames = frame_data.get("frames", [])
    total = len(frames)

    # If limit is None or 0, return all frames from offset
    if limit is None or limit == 0:
        result_frames = frames[offset:]
    else:
        result_frames = frames[offset:offset + limit]

    return {
        "job_id": job_id,
        "video_info": frame_data.get("video_info"),
        "thresholds_used": frame_data.get("thresholds_used"),
        "total_frames": total,
        "offset": offset,
        "limit": limit if limit else total,
        "frames": result_frames
    }


@router.post("/jobs/{job_id}/reclassify")
async def reclassify_job(
    job_id: int,
    request: ReclassifyRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Re-classify shots for a job with new thresholds."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    frame_data = _load_job_frame_data(job)
    if not frame_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Frame data not available. Re-run analysis with 'Enable tuning data' checked."
        )

    # Re-classify
    results = reclassify_shots(
        frame_data=frame_data,
        new_thresholds=request.velocity_thresholds,
        new_cooldown=request.shot_cooldown_seconds,
        position_thresholds=request.position_thresholds
    )

    return results


@router.get("/jobs/{job_id}/video/url")
async def get_job_video_url(
    job_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get URL for the source video of a job (for tuning playback).

    Always returns the proxy URL to avoid CORS issues with S3.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from ..services.storage_service import get_storage_service
    storage = get_storage_service()

    if storage.is_s3():
        # For S3, check if video exists and return proxy URL (avoid CORS issues)
        s3_key = job.s3_video_key
        if not s3_key:
            raise HTTPException(status_code=404, detail="S3 video key not set")
        try:
            import boto3
            s3_client = boto3.client('s3')
            s3_client.head_object(Bucket=storage.uploads.bucket, Key=s3_key)
            # Return proxy URL instead of presigned URL to avoid CORS
            return {"url": f"/api/v1/tuning/jobs/{job_id}/video", "expires_in": None}
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Video not found: {e}")
    else:
        # For local storage, return the API endpoint
        if not job.video_path or not Path(job.video_path).exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        return {"url": f"/api/v1/tuning/jobs/{job_id}/video", "expires_in": None}


@router.get("/jobs/{job_id}/video")
async def get_job_video(
    job_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Stream the source video for a job (for tuning playback)."""
    from fastapi.responses import FileResponse, StreamingResponse

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from ..services.storage_service import get_storage_service
    storage = get_storage_service()

    # Check if video is in S3
    if storage.is_s3():
        # For S3, use s3_video_key (not video_path which is empty for S3 uploads)
        s3_key = job.s3_video_key
        if not s3_key:
            raise HTTPException(status_code=404, detail="S3 video key not set")

        try:
            logger.info(f"Loading video from S3: {s3_key}")
            video_data = storage.uploads.load(s3_key)

            def iter_content():
                yield video_data

            return StreamingResponse(
                iter_content(),
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f'inline; filename="{job.video_filename}"',
                    "Content-Length": str(len(video_data))
                }
            )
        except Exception as e:
            logger.error(f"Failed to load video from S3: {e}")
            raise HTTPException(status_code=404, detail=f"Video not found in S3: {e}")
    else:
        # Local file
        if not job.video_path or not Path(job.video_path).exists():
            raise HTTPException(status_code=404, detail="Video file not found")

        return FileResponse(
            job.video_path,
            media_type="video/mp4",
            filename=job.video_filename
        )


@router.get("/jobs/{job_id}/annotated-video/url")
async def get_job_annotated_video_url(
    job_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get URL for the annotated video of a job (with pose overlay).

    Always returns the proxy URL to avoid CORS issues with S3.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.annotated_video_path:
        raise HTTPException(status_code=404, detail="Annotated video not available for this job")

    from ..services.storage_service import get_storage_service
    storage = get_storage_service()

    if storage.is_s3():
        # Check if the file exists in S3 (without returning presigned URL to avoid CORS)
        try:
            # Just verify it exists by checking if we can get metadata
            import boto3
            s3_client = boto3.client('s3')
            s3_client.head_object(Bucket=storage.outputs.bucket, Key=job.annotated_video_path)
            # Return proxy URL instead of presigned URL to avoid CORS
            return {"url": f"/api/v1/tuning/jobs/{job_id}/annotated-video", "expires_in": None}
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Annotated video not found: {e}")
    else:
        if not Path(job.annotated_video_path).exists():
            raise HTTPException(status_code=404, detail="Annotated video file not found")
        return {"url": f"/api/v1/tuning/jobs/{job_id}/annotated-video", "expires_in": None}


@router.get("/jobs/{job_id}/annotated-video")
async def get_job_annotated_video(
    job_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Stream the annotated video for a job (with pose overlay and shot detection).

    For local files, automatically re-encodes mp4v to browser-compatible H.264 on first request.
    The H.264 version is cached so subsequent requests are fast.
    """
    from fastapi.responses import FileResponse, StreamingResponse

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.annotated_video_path:
        raise HTTPException(status_code=404, detail="Annotated video not available for this job")

    from ..services.storage_service import get_storage_service
    storage = get_storage_service()

    if storage.is_s3():
        import subprocess
        import tempfile
        import os

        try:
            logger.info(f"Loading annotated video from S3: {job.annotated_video_path}")

            # Check if we have a cached H.264 version in S3
            h264_s3_key = job.annotated_video_path.replace('.mp4', '_h264.mp4')
            h264_exists = False
            try:
                import boto3
                s3_client = boto3.client('s3')
                s3_client.head_object(Bucket=storage.outputs.bucket, Key=h264_s3_key)
                h264_exists = True
                logger.info(f"Found cached H.264 version in S3: {h264_s3_key}")
            except Exception:
                pass

            if h264_exists:
                # Use cached H.264 version
                video_data = storage.outputs.load(h264_s3_key)
            else:
                # Download, re-encode, and upload H.264 version
                logger.info("Re-encoding S3 annotated video to H.264 for browser compatibility...")
                video_data = storage.outputs.load(job.annotated_video_path)

                # Create temp files for re-encoding
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_in:
                    tmp_in.write(video_data)
                    tmp_in_path = tmp_in.name

                tmp_out_path = tmp_in_path.replace('.mp4', '_h264.mp4')

                try:
                    cmd = [
                        'ffmpeg', '-y',
                        '-loglevel', 'warning',
                        '-i', tmp_in_path,
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart',
                        tmp_out_path
                    ]
                    subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=True)
                    logger.info("H.264 re-encoding successful")

                    # Read the re-encoded file
                    with open(tmp_out_path, 'rb') as f:
                        video_data = f.read()

                    # Upload H.264 version to S3 for future use (async/background would be better)
                    try:
                        storage.outputs.save(h264_s3_key, video_data)
                        logger.info(f"Cached H.264 version to S3: {h264_s3_key}")
                    except Exception as upload_err:
                        logger.warning(f"Failed to cache H.264 to S3: {upload_err}")

                except subprocess.CalledProcessError as e:
                    logger.error(f"H.264 re-encoding failed: {e.stderr}")
                    # Fall back to original (won't play in browser but at least won't error)
                finally:
                    # Clean up temp files
                    if os.path.exists(tmp_in_path):
                        os.unlink(tmp_in_path)
                    if os.path.exists(tmp_out_path):
                        os.unlink(tmp_out_path)

            def iter_content():
                yield video_data

            return StreamingResponse(
                iter_content(),
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f'inline; filename="analyzed_{job.video_filename}"',
                    "Content-Length": str(len(video_data))
                }
            )
        except Exception as e:
            logger.error(f"Failed to load annotated video from S3: {e}")
            raise HTTPException(status_code=404, detail=f"Annotated video not found in S3: {e}")
    else:
        video_path = Path(job.annotated_video_path)
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Annotated video file not found")

        # Check if we need to re-encode to H.264 for browser compatibility
        # OpenCV's mp4v codec is not supported by browsers
        # The H.264 version is cached with _h264 suffix
        h264_path = video_path.parent / f"{video_path.stem}_h264{video_path.suffix}"

        if h264_path.exists():
            # Use existing H.264 version
            logger.info(f"Serving cached H.264 annotated video: {h264_path}")
            serve_path = h264_path
        else:
            # Re-encode on demand (only happens once per video)
            logger.info(f"Re-encoding annotated video to H.264 for browser compatibility...")
            import subprocess
            try:
                cmd = [
                    'ffmpeg', '-y',
                    '-loglevel', 'warning',
                    '-i', str(video_path),
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    str(h264_path)
                ]
                subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=True)
                logger.info(f"Created H.264 version: {h264_path}")
                serve_path = h264_path
            except Exception as e:
                logger.warning(f"Failed to create H.264 version: {e}, serving original (may not play in browser)")
                serve_path = video_path

        return FileResponse(
            str(serve_path),
            media_type="video/mp4",
            filename=f"analyzed_{job.video_filename}"
        )


# ============================================================================
# Live Stream Tuning Endpoints
# ============================================================================

@router.get("/live/sessions")
async def list_active_stream_sessions(
    current_user: User = Depends(get_admin_user)
):
    """List all active streaming sessions available for tuning."""
    from ..services.stream_service import get_stream_session_manager

    session_manager = get_stream_session_manager()
    active_ids = session_manager.get_active_sessions()

    sessions = []
    for session_id in active_ids:
        analyzer = session_manager.get_session(session_id)
        if analyzer:
            sessions.append({
                "session_id": session_id,
                "frames_processed": analyzer.stats.frames_processed,
                "total_shots": analyzer.stats.total_shots,
                "current_thresholds": analyzer.get_current_thresholds()
            })

    return {"active_sessions": sessions}


@router.get("/live/{session_id}/thresholds")
async def get_live_session_thresholds(
    session_id: int,
    current_user: User = Depends(get_admin_user)
):
    """Get current thresholds for an active streaming session."""
    from ..services.stream_service import get_stream_session_manager

    session_manager = get_stream_session_manager()
    analyzer = session_manager.get_session(session_id)

    if not analyzer:
        raise HTTPException(status_code=404, detail="Stream session not found or not active")

    return {
        "session_id": session_id,
        "thresholds": analyzer.get_current_thresholds(),
        "stats": {
            "frames_processed": analyzer.stats.frames_processed,
            "total_shots": analyzer.stats.total_shots,
            "player_detection_rate": (
                analyzer.stats.player_detected_frames / analyzer.stats.frames_processed
                if analyzer.stats.frames_processed > 0 else 0
            )
        }
    }


@router.post("/live/{session_id}/update-thresholds")
async def update_live_session_thresholds(
    session_id: int,
    request: ReclassifyRequest,
    current_user: User = Depends(get_admin_user)
):
    """
    Update thresholds for an active streaming session.

    Changes take effect immediately on all future frames.
    This is the key feature of live tuning - no need to restart the stream.
    """
    from ..services.stream_service import get_stream_session_manager

    session_manager = get_stream_session_manager()
    success = session_manager.update_session_thresholds(
        session_id=session_id,
        velocity_thresholds=request.velocity_thresholds,
        position_thresholds=request.position_thresholds,
        shot_cooldown_seconds=request.shot_cooldown_seconds
    )

    if not success:
        raise HTTPException(status_code=404, detail="Stream session not found or not active")

    logger.info(f"Updated live session {session_id} thresholds")

    return {
        "status": "updated",
        "session_id": session_id,
        "message": "Thresholds updated. Changes apply to all future frames immediately."
    }
