"""Job manager for background task processing."""

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Callable
from functools import partial

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db_models.job import Job, JobStatus
from .analyzer_service import AnalyzerService

settings = get_settings()
logger = logging.getLogger(__name__)


def _run_analysis_process(
    video_path: str,
    court_boundary: Dict[str, Any],
    output_dir: str,
    speed_preset: str,
    background_frame_path: str = None
) -> Dict[str, Any]:
    """Run analysis in a separate process."""
    return AnalyzerService.run_analysis(
        video_path=video_path,
        court_boundary=court_boundary,
        output_dir=Path(output_dir),
        speed_preset=speed_preset,
        background_frame_path=background_frame_path
    )


class JobManager:
    """Manages background analysis jobs."""

    _instance = None
    _executor: Optional[ProcessPoolExecutor] = None
    _active_jobs: Dict[int, asyncio.Task] = {}
    _progress_callbacks: Dict[int, Callable[[int, float, str], None]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._executor = ProcessPoolExecutor(max_workers=settings.max_concurrent_jobs)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "JobManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_progress_callback(self, job_id: int, callback: Callable[[int, float, str], None]):
        """Register a callback for progress updates."""
        self._progress_callbacks[job_id] = callback

    def unregister_progress_callback(self, job_id: int):
        """Unregister progress callback."""
        self._progress_callbacks.pop(job_id, None)

    async def _notify_progress(self, job_id: int, progress: float, message: str):
        """Notify registered callbacks of progress."""
        if job_id in self._progress_callbacks:
            try:
                await self._progress_callbacks[job_id](job_id, progress, message)
            except Exception as e:
                logger.error(f"Error in progress callback for job {job_id}: {e}")

    async def start_job(
        self,
        db: Session,
        job: Job,
        speed_preset: str = "balanced"
    ) -> bool:
        """Start an analysis job."""
        if job.status != JobStatus.PENDING:
            return False

        if job.court_boundary is None:
            return False

        # Update job status
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.progress = 0.0
        job.status_message = "Starting analysis..."
        db.commit()

        # Create output directory for this job
        output_dir = settings.output_path / str(job.user_id) / str(job.id)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Start async task
        task = asyncio.create_task(
            self._run_job_async(
                job_id=job.id,
                user_id=job.user_id,
                video_path=job.video_path,
                court_boundary=job.court_boundary,
                output_dir=str(output_dir),
                speed_preset=speed_preset,
                background_frame_path=job.background_frame_path
            )
        )
        self._active_jobs[job.id] = task

        return True

    async def _run_job_async(
        self,
        job_id: int,
        user_id: int,
        video_path: str,
        court_boundary: Dict[str, Any],
        output_dir: str,
        speed_preset: str,
        background_frame_path: str = None
    ):
        """Run analysis job asynchronously."""
        from ..database import SessionLocal

        loop = asyncio.get_event_loop()
        progress_file = Path(output_dir) / "progress.json"

        try:
            await self._notify_progress(job_id, 5.0, "Initializing analyzer...")

            # Start progress polling task
            polling_task = asyncio.create_task(
                self._poll_progress(job_id, str(progress_file))
            )

            # Run in process pool
            result = await loop.run_in_executor(
                self._executor,
                partial(
                    _run_analysis_process,
                    video_path=video_path,
                    court_boundary=court_boundary,
                    output_dir=output_dir,
                    speed_preset=speed_preset,
                    background_frame_path=background_frame_path
                )
            )

            # Stop polling
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass

            await self._notify_progress(job_id, 95.0, "Saving results...")

            # Update job with results
            db = SessionLocal()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = JobStatus.COMPLETED
                    job.progress = 100.0
                    job.completed_at = datetime.utcnow()
                    job.status_message = "Analysis complete"
                    job.report_path = result.get("report_path")
                    job.annotated_video_path = result.get("annotated_video_path")
                    # Use heatmap_paths from result (all 4 types), fallback to old single heatmap
                    job.heatmap_paths = result.get("heatmap_paths") or {
                        "movement": result.get("heatmap_image_path")
                    }
                    db.commit()

                    await self._notify_progress(job_id, 100.0, "Complete!")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")

            db = SessionLocal()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.status_message = "Analysis failed"
                    db.commit()

                    await self._notify_progress(job_id, -1, f"Failed: {e}")
            finally:
                db.close()

        finally:
            self._active_jobs.pop(job_id, None)
            self.unregister_progress_callback(job_id)

    async def _poll_progress(self, job_id: int, progress_file: str):
        """Poll progress file and update database/WebSocket."""
        from ..database import SessionLocal

        last_progress = 0.0

        while True:
            try:
                await asyncio.sleep(5)  # Poll every 5 seconds

                progress_data = AnalyzerService.read_progress_file(progress_file)
                if progress_data:
                    progress = progress_data.get('progress', 0)
                    message = progress_data.get('message', 'Processing...')

                    # Only update if progress changed
                    if progress > last_progress:
                        last_progress = progress

                        # Update database
                        db = SessionLocal()
                        try:
                            job = db.query(Job).filter(Job.id == job_id).first()
                            if job and job.status == JobStatus.PROCESSING:
                                job.progress = progress
                                job.status_message = message
                                db.commit()
                        finally:
                            db.close()

                        # Notify WebSocket
                        await self._notify_progress(job_id, progress, message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling progress for job {job_id}: {e}")

    async def cancel_job(self, db: Session, job: Job) -> bool:
        """Cancel a running job."""
        if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            return False

        # Cancel the task if running
        if job.id in self._active_jobs:
            self._active_jobs[job.id].cancel()
            self._active_jobs.pop(job.id, None)

        job.status = JobStatus.CANCELLED
        job.status_message = "Cancelled by user"
        db.commit()

        return True

    def is_job_active(self, job_id: int) -> bool:
        """Check if a job is currently active."""
        return job_id in self._active_jobs

    def shutdown(self):
        """Shutdown the executor."""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
