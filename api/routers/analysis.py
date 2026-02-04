"""Analysis router for video upload and job management."""

import logging
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..db_models.job import Job, JobStatus
from ..models.job import JobResponse, JobListResponse
from ..models.analysis import AnalysisStart, AnalysisStatus
from ..services.job_manager import JobManager
from ..services.storage_service import get_storage_service
from ..websocket.progress_handler import get_ws_manager
from .auth import get_current_user

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
settings = get_settings()
logger = logging.getLogger(__name__)


def get_job_manager() -> JobManager:
    """Get job manager instance."""
    return JobManager.get_instance()


@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a video file for analysis."""
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_video_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_video_extensions)}"
        )

    import uuid
    unique_filename = f"{uuid.uuid4()}{file_ext}"

    storage = get_storage_service()
    logger.info(f"Storage type: {storage.storage_type}, is_s3: {storage.is_s3()}")

    if storage.is_s3():
        # Upload to S3
        s3_key = storage.get_upload_path(current_user.id, unique_filename)
        logger.info(f"Uploading to S3: bucket={settings.s3_bucket}, key={s3_key}")
        try:
            # Read file content and upload to S3
            file_content = await file.read()
            content_type = file.content_type or "video/mp4"
            logger.info(f"File size: {len(file_content)} bytes, content_type: {content_type}")
            storage.uploads.save(s3_key, file_content, content_type=content_type)
            logger.info(f"Successfully uploaded to S3: {s3_key}")
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to S3: {str(e)}"
            )

        # Create job record with S3 storage
        job = Job(
            user_id=current_user.id,
            video_filename=file.filename,
            video_path="",  # Not used for S3
            storage_type="s3",
            s3_video_key=s3_key,
            status=JobStatus.PENDING
        )
        logger.info(f"Created job with S3 storage: job_id will be assigned, s3_key={s3_key}")
    else:
        # Save to local filesystem
        logger.info("Using local storage")
        user_upload_dir = settings.upload_path / str(current_user.id)
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_upload_dir / unique_filename

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(f"Saved file locally: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save file locally: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )

        # Create job record with local storage
        job = Job(
            user_id=current_user.id,
            video_filename=file.filename,
            video_path=str(file_path),
            storage_type="local",
            status=JobStatus.PENDING
        )

    db.add(job)
    db.commit()
    db.refresh(job)

    return JobResponse.from_orm_with_results(job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's analysis jobs."""
    query = db.query(Job).filter(Job.user_id == current_user.id)

    if status_filter:
        try:
            status_enum = JobStatus(status_filter)
            query = query.filter(Job.status == status_enum)
        except ValueError:
            pass

    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()

    return JobListResponse(
        jobs=[JobResponse.from_orm_with_results(j) for j in jobs],
        total=total
    )


@router.post("/start/{job_id}", response_model=AnalysisStatus)
async def start_analysis(
    job_id: int,
    analysis_config: AnalysisStart,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    job_manager: JobManager = Depends(get_job_manager)
):
    """Start analysis for a job with court boundary."""
    from ..services.analyzer_service import AnalyzerService

    # Get job
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not in pending state (current: {job.status.value})"
        )

    # Save court boundary
    boundary = analysis_config.court_boundary
    job.court_boundary = {
        "top_left": boundary.top_left,
        "top_right": boundary.top_right,
        "bottom_left": boundary.bottom_left,
        "bottom_right": boundary.bottom_right,
        "court_color": boundary.court_color
    }

    # Save background frame for heatmaps (use the frame user selected for court setup)
    output_dir = settings.output_path / str(current_user.id) / str(job.id)
    output_dir.mkdir(parents=True, exist_ok=True)
    background_frame_path = str(output_dir / "background_frame.png")

    # Determine video path for frame extraction
    storage = get_storage_service()
    temp_video_path = None

    if job.storage_type == "s3" and job.s3_video_key:
        # Download video temporarily for frame extraction
        temp_video_path = str(output_dir / f"temp_{job.video_filename}")
        try:
            video_data = storage.uploads.load(job.s3_video_key)
            with open(temp_video_path, 'wb') as f:
                f.write(video_data)
            video_path_for_frame = temp_video_path
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download video from S3: {str(e)}"
            )
    else:
        video_path_for_frame = job.video_path

    # Extract and save frame at the timestamp user was viewing
    if AnalyzerService.save_frame_to_file(video_path_for_frame, background_frame_path, timestamp=analysis_config.frame_timestamp):
        job.background_frame_path = background_frame_path

    # Clean up temp video file (will be downloaded again during analysis)
    if temp_video_path and Path(temp_video_path).exists():
        Path(temp_video_path).unlink()

    db.commit()

    # Register WebSocket progress callback
    ws_manager = get_ws_manager()

    async def progress_callback(job_id: int, progress: float, message: str):
        await ws_manager.send_progress(job_id, progress, message)

    job_manager.register_progress_callback(job_id, progress_callback)

    # Start job
    success = await job_manager.start_job(db, job, analysis_config.speed_preset)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to start job")

    db.refresh(job)

    return AnalysisStatus(
        job_id=job.id,
        status=job.status.value,
        progress=job.progress,
        status_message=job.status_message
    )


@router.get("/status/{job_id}", response_model=AnalysisStatus)
async def get_job_status(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job status and progress."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return AnalysisStatus(
        job_id=job.id,
        status=job.status.value,
        progress=job.progress,
        status_message=job.status_message,
        error_message=job.error_message
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    job_manager: JobManager = Depends(get_job_manager)
):
    """Cancel a running job without deleting it."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status.value}"
        )

    await job_manager.cancel_job(db, job)

    return {"message": "Job cancelled", "job_id": job_id}


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    job_manager: JobManager = Depends(get_job_manager)
):
    """Cancel and delete a job."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Cancel if running
    if job.status == JobStatus.PROCESSING:
        await job_manager.cancel_job(db, job)

    storage = get_storage_service()

    if job.storage_type == "s3":
        # Delete S3 files
        if job.s3_video_key:
            storage.uploads.delete(job.s3_video_key)

        if job.report_path:
            storage.outputs.delete(job.report_path)

        if job.annotated_video_path:
            storage.outputs.delete(job.annotated_video_path)

        if job.heatmap_paths:
            for heatmap_path in job.heatmap_paths.values():
                if heatmap_path:
                    storage.outputs.delete(heatmap_path)
    else:
        # Delete local files
        if job.video_path and Path(job.video_path).exists():
            Path(job.video_path).unlink()

        if job.report_path and Path(job.report_path).exists():
            Path(job.report_path).unlink()

        if job.annotated_video_path and Path(job.annotated_video_path).exists():
            Path(job.annotated_video_path).unlink()

        if job.heatmap_paths:
            for heatmap_path in job.heatmap_paths.values():
                if heatmap_path and Path(heatmap_path).exists():
                    Path(heatmap_path).unlink()

    # Delete job record
    db.delete(job)
    db.commit()
