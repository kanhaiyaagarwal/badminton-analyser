"""Results router for retrieving analysis results."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models.job import Job, JobStatus
from ..models.analysis import AnalysisReport, RallyInfo, ShotInfo, AnalysisSummary
from .auth import get_current_user

router = APIRouter(prefix="/api/v1/results", tags=["results"])


def get_user_job(job_id: int, user_id: int, db: Session) -> Job:
    """Get job belonging to user."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


def require_completed_job(job: Job) -> Job:
    """Ensure job is completed."""
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed (status: {job.status.value})"
        )
    return job


@router.get("/{job_id}")
async def get_full_report(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full analysis report."""
    job = get_user_job(job_id, current_user.id, db)
    require_completed_job(job)

    if not job.report_path or not Path(job.report_path).exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(job.report_path, 'r') as f:
        report = json.load(f)

    return report


@router.get("/{job_id}/summary")
async def get_summary(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis summary only."""
    job = get_user_job(job_id, current_user.id, db)
    require_completed_job(job)

    if not job.report_path or not Path(job.report_path).exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(job.report_path, 'r') as f:
        report = json.load(f)

    return {
        "summary": report.get("summary", {}),
        "shot_distribution": report.get("shot_distribution", {})
    }


@router.get("/{job_id}/rallies")
async def get_rallies(
    job_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get rally breakdown."""
    job = get_user_job(job_id, current_user.id, db)
    require_completed_job(job)

    if not job.report_path or not Path(job.report_path).exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(job.report_path, 'r') as f:
        report = json.load(f)

    rallies = report.get("rallies", [])

    return {
        "rallies": rallies[skip:skip + limit],
        "total": len(rallies)
    }


@router.get("/{job_id}/timeline")
async def get_shot_timeline(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get shot timeline."""
    job = get_user_job(job_id, current_user.id, db)
    require_completed_job(job)

    if not job.report_path or not Path(job.report_path).exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(job.report_path, 'r') as f:
        report = json.load(f)

    return {
        "timeline": report.get("shot_timeline", [])
    }


@router.get("/{job_id}/heatmap/{heatmap_type}")
async def get_heatmap(
    job_id: int,
    heatmap_type: str = "movement",
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get heatmap image."""
    job = get_user_job(job_id, current_user.id, db)
    require_completed_job(job)

    if not job.heatmap_paths:
        raise HTTPException(status_code=404, detail="No heatmaps available")

    heatmap_path = job.heatmap_paths.get(heatmap_type)
    if not heatmap_path or not Path(heatmap_path).exists():
        raise HTTPException(status_code=404, detail=f"Heatmap '{heatmap_type}' not found")

    return FileResponse(
        heatmap_path,
        media_type="image/png",
        filename=f"heatmap_{heatmap_type}_{job_id}.png"
    )


@router.get("/{job_id}/heatmaps")
async def list_heatmaps(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List available heatmap types."""
    job = get_user_job(job_id, current_user.id, db)
    require_completed_job(job)

    if not job.heatmap_paths:
        return {"heatmaps": []}

    available = []
    for heatmap_type, path in job.heatmap_paths.items():
        if path and Path(path).exists():
            available.append({
                "type": heatmap_type,
                "url": f"/api/v1/results/{job_id}/heatmap/{heatmap_type}"
            })

    return {"heatmaps": available}


@router.get("/{job_id}/video")
async def get_annotated_video(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get annotated video file."""
    job = get_user_job(job_id, current_user.id, db)
    require_completed_job(job)

    if not job.annotated_video_path or not Path(job.annotated_video_path).exists():
        raise HTTPException(status_code=404, detail="Annotated video not found")

    return FileResponse(
        job.annotated_video_path,
        media_type="video/mp4",
        filename=f"analyzed_{job.video_filename}"
    )
