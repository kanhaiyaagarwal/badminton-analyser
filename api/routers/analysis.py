"""Analysis router for video upload and job management."""

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
from ..websocket.progress_handler import get_ws_manager
from .auth import get_current_user

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
settings = get_settings()


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

    # Create user upload directory
    user_upload_dir = settings.upload_path / str(current_user.id)
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    import uuid
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = user_upload_dir / unique_filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Create job record
    job = Job(
        user_id=current_user.id,
        video_filename=file.filename,
        video_path=str(file_path),
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

    # Extract and save frame at the timestamp user was viewing
    if AnalyzerService.save_frame_to_file(job.video_path, background_frame_path, timestamp=analysis_config.frame_timestamp):
        job.background_frame_path = background_frame_path

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

    # Delete associated files
    if job.video_path and Path(job.video_path).exists():
        Path(job.video_path).unlink()

    if job.report_path and Path(job.report_path).exists():
        Path(job.report_path).unlink()

    if job.annotated_video_path and Path(job.annotated_video_path).exists():
        Path(job.annotated_video_path).unlink()

    # Delete job record
    db.delete(job)
    db.commit()
