"""Upload router for S3 pre-signed URL uploads."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models.job import Job, JobStatus
from ..services.s3_service import get_s3_service
from ..services.storage_service import get_storage_service
from ..config import get_settings
from .auth import get_current_user


router = APIRouter(prefix="/api/v1/upload", tags=["upload"])


# Request/Response models
class UploadRequest(BaseModel):
    """Request for upload URL."""
    filename: str
    content_type: str
    size: int  # File size in bytes


class UploadResponse(BaseModel):
    """Response with upload URL."""
    upload_url: str
    file_key: str
    job_id: int
    expires_in: int
    use_multipart: bool = False


class MultipartInitRequest(BaseModel):
    """Request to initiate multipart upload."""
    filename: str
    content_type: str
    size: int


class MultipartInitResponse(BaseModel):
    """Response with multipart upload details."""
    upload_id: str
    file_key: str
    job_id: int
    part_urls: List[dict]
    part_count: int
    part_size: int


class MultipartPart(BaseModel):
    """Single part info for completing multipart upload."""
    PartNumber: int
    ETag: str


class MultipartCompleteRequest(BaseModel):
    """Request to complete multipart upload."""
    file_key: str
    upload_id: str
    parts: List[MultipartPart]


class ConfirmUploadRequest(BaseModel):
    """Request to confirm upload completion."""
    court_boundary: Optional[dict] = None


@router.post("/request", response_model=UploadResponse)
async def request_upload_url(
    request: UploadRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request a pre-signed URL for direct S3 upload.

    For files > 100MB, use /multipart/init instead.
    """
    settings = get_settings()
    storage = get_storage_service()
    s3_service = get_s3_service()

    # Validate file extension
    ext = '.' + request.filename.rsplit('.', 1)[-1].lower() if '.' in request.filename else ''
    if ext not in settings.allowed_video_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {settings.allowed_video_extensions}"
        )

    # Validate file size
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if request.size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {settings.max_upload_size_mb}MB"
        )

    # Check if S3 is enabled
    if not s3_service.is_enabled():
        raise HTTPException(
            status_code=400,
            detail="S3 upload not available. Use standard upload endpoint."
        )

    # Recommend multipart for large files
    use_multipart = request.size > 100 * 1024 * 1024  # > 100MB

    # Generate upload URL
    upload_info = s3_service.generate_upload_url(
        user_id=current_user.id,
        filename=request.filename,
        content_type=request.content_type
    )

    # Create pending job
    job = Job(
        user_id=current_user.id,
        video_filename=request.filename,
        video_path="",  # Will be set after upload confirmation
        storage_type="s3",
        s3_video_key=upload_info['file_key'],
        status=JobStatus.PENDING,
        status_message="Waiting for upload"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return UploadResponse(
        upload_url=upload_info['upload_url'],
        file_key=upload_info['file_key'],
        job_id=job.id,
        expires_in=upload_info['expires_in'],
        use_multipart=use_multipart
    )


@router.post("/multipart/init", response_model=MultipartInitResponse)
async def init_multipart_upload(
    request: MultipartInitRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate multipart upload for large files (>100MB).

    Returns part URLs that client can upload to in parallel.
    """
    settings = get_settings()
    s3_service = get_s3_service()

    # Validate file extension
    ext = '.' + request.filename.rsplit('.', 1)[-1].lower() if '.' in request.filename else ''
    if ext not in settings.allowed_video_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {settings.allowed_video_extensions}"
        )

    # Validate file size
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if request.size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {settings.max_upload_size_mb}MB"
        )

    if not s3_service.is_enabled():
        raise HTTPException(
            status_code=400,
            detail="S3 upload not available. Use standard upload endpoint."
        )

    # Initiate multipart upload
    upload_info = s3_service.generate_multipart_upload(
        user_id=current_user.id,
        filename=request.filename,
        content_type=request.content_type,
        file_size=request.size
    )

    # Create pending job
    job = Job(
        user_id=current_user.id,
        video_filename=request.filename,
        video_path="",
        storage_type="s3",
        s3_video_key=upload_info['file_key'],
        status=JobStatus.PENDING,
        status_message="Multipart upload in progress"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return MultipartInitResponse(
        upload_id=upload_info['upload_id'],
        file_key=upload_info['file_key'],
        job_id=job.id,
        part_urls=upload_info['part_urls'],
        part_count=upload_info['part_count'],
        part_size=upload_info['part_size']
    )


@router.post("/multipart/complete")
async def complete_multipart_upload(
    request: MultipartCompleteRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete multipart upload after all parts are uploaded.
    """
    s3_service = get_s3_service()

    if not s3_service.is_enabled():
        raise HTTPException(status_code=400, detail="S3 not available")

    # Find the job with this file key
    job = db.query(Job).filter(
        Job.s3_video_key == request.file_key,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found for this upload")

    try:
        # Complete the multipart upload
        parts = [{"PartNumber": p.PartNumber, "ETag": p.ETag} for p in request.parts]
        result = s3_service.complete_multipart_upload(
            file_key=request.file_key,
            upload_id=request.upload_id,
            parts=parts
        )

        job.status_message = "Upload complete, waiting for confirmation"
        db.commit()

        return {
            "status": "success",
            "file_key": result['file_key'],
            "job_id": job.id
        }

    except Exception as e:
        # Abort the upload on failure
        try:
            s3_service.abort_multipart_upload(request.file_key, request.upload_id)
        except Exception:
            pass

        job.status = JobStatus.FAILED
        job.error_message = f"Multipart upload failed: {str(e)}"
        db.commit()

        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/confirm/{job_id}")
async def confirm_upload(
    job_id: int,
    request: ConfirmUploadRequest = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirm that upload is complete and optionally set court boundary.

    This triggers the job to be ready for processing.
    """
    s3_service = get_s3_service()

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

    # Verify file exists in S3
    if job.storage_type == "s3" and job.s3_video_key:
        if not s3_service.file_exists(job.s3_video_key):
            raise HTTPException(status_code=400, detail="Upload not found in S3")

    # Update job
    if request and request.court_boundary:
        job.court_boundary = request.court_boundary

    job.status_message = "Upload confirmed, ready for processing"
    db.commit()

    return {
        "status": "success",
        "job_id": job.id,
        "message": "Upload confirmed. Set court boundary and start analysis."
    }


@router.get("/status")
async def get_upload_status(current_user=Depends(get_current_user)):
    """Check if S3 upload is available."""
    s3_service = get_s3_service()
    settings = get_settings()

    return {
        "s3_enabled": s3_service.is_enabled(),
        "max_upload_size_mb": settings.max_upload_size_mb,
        "allowed_extensions": list(settings.allowed_video_extensions),
        "multipart_threshold_mb": 100
    }
