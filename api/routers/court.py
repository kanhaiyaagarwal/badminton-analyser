"""Court boundary router."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..db_models.job import Job
from ..models.court import CourtBoundary, CourtBoundaryCreate
from ..services.analyzer_service import AnalyzerService
from ..services.storage_service import get_storage_service
from .auth import get_current_user

router = APIRouter(prefix="/api/v1/court", tags=["court"])
logger = logging.getLogger(__name__)
settings = get_settings()


def get_video_path_for_job(job: Job) -> str:
    """Get local video path for a job, downloading from S3 if needed."""
    if job.storage_type == "s3" and job.s3_video_key:
        # For S3, we need to download to a temp location
        storage = get_storage_service()
        temp_dir = settings.output_path / str(job.user_id) / str(job.id)
        temp_dir.mkdir(parents=True, exist_ok=True)
        local_path = temp_dir / f"temp_{job.video_filename}"

        # Download if not already cached
        if not local_path.exists():
            logger.info(f"Downloading video from S3 for court setup: {job.s3_video_key}")
            video_data = storage.uploads.load(job.s3_video_key)
            with open(local_path, 'wb') as f:
                f.write(video_data)
            logger.info(f"Downloaded video to: {local_path}")

        return str(local_path)
    else:
        return job.video_path


@router.post("/extract-frame/{job_id}")
async def extract_frame(
    job_id: int,
    timestamp: float = 0.0,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract a frame from the video for court selection."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get video path (download from S3 if needed)
    try:
        video_path = get_video_path_for_job(job)
    except Exception as e:
        logger.error(f"Failed to get video for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to access video: {str(e)}")

    # Get video info
    video_info = AnalyzerService.get_video_info(video_path)
    if not video_info:
        raise HTTPException(status_code=400, detail="Could not read video")

    # Validate timestamp
    if timestamp < 0 or timestamp > video_info["duration"]:
        raise HTTPException(status_code=400, detail="Invalid timestamp")

    # Extract frame
    frame_bytes = AnalyzerService.extract_frame(video_path, timestamp)
    if frame_bytes is None:
        raise HTTPException(status_code=400, detail="Failed to extract frame")

    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={
            "X-Video-Width": str(video_info["width"]),
            "X-Video-Height": str(video_info["height"]),
            "X-Video-Duration": str(video_info["duration"]),
            "X-Video-FPS": str(video_info["fps"])
        }
    )


@router.get("/video-info/{job_id}")
async def get_video_info(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get video metadata."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get video path (download from S3 if needed)
    try:
        video_path = get_video_path_for_job(job)
    except Exception as e:
        logger.error(f"Failed to get video for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to access video: {str(e)}")

    video_info = AnalyzerService.get_video_info(video_path)
    if not video_info:
        raise HTTPException(status_code=400, detail="Could not read video")

    return video_info


@router.post("/boundary/{job_id}", response_model=CourtBoundary)
async def save_boundary(
    job_id: int,
    boundary: CourtBoundaryCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save court boundary for a job."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Validate boundary points
    points = [boundary.top_left, boundary.top_right, boundary.bottom_left, boundary.bottom_right]
    for point in points:
        if len(point) != 2:
            raise HTTPException(status_code=400, detail="Each point must have exactly 2 coordinates")
        if point[0] < 0 or point[1] < 0:
            raise HTTPException(status_code=400, detail="Coordinates must be non-negative")

    # Save to job
    job.court_boundary = {
        "top_left": boundary.top_left,
        "top_right": boundary.top_right,
        "bottom_left": boundary.bottom_left,
        "bottom_right": boundary.bottom_right,
        "court_color": boundary.court_color
    }
    db.commit()

    return boundary.to_boundary()


@router.get("/boundary/{job_id}", response_model=CourtBoundary)
async def get_boundary(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get saved court boundary for a job."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.court_boundary:
        raise HTTPException(status_code=404, detail="No boundary saved for this job")

    return CourtBoundary(
        top_left=tuple(job.court_boundary["top_left"]),
        top_right=tuple(job.court_boundary["top_right"]),
        bottom_left=tuple(job.court_boundary["bottom_left"]),
        bottom_right=tuple(job.court_boundary["bottom_right"]),
        court_color=job.court_boundary.get("court_color", "green")
    )
