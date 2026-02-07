"""Job manager for background task processing."""

import asyncio
import logging
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Callable
from functools import partial

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db_models.job import Job, JobStatus
from .analyzer_service import AnalyzerService
from .storage_service import get_storage_service
from .s3_service import get_s3_service

settings = get_settings()
logger = logging.getLogger(__name__)


def _run_analysis_process(
    video_path: str,
    court_boundary: Dict[str, Any],
    output_dir: str,
    speed_preset: str,
    background_frame_path: str = None,
    save_frame_data: bool = False
) -> Dict[str, Any]:
    """Run analysis in a separate process."""
    return AnalyzerService.run_analysis(
        video_path=video_path,
        court_boundary=court_boundary,
        output_dir=Path(output_dir),
        speed_preset=speed_preset,
        background_frame_path=background_frame_path,
        save_frame_data=save_frame_data
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
        speed_preset: str = "balanced",
        save_frame_data: bool = False
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

        # Determine video path - download from S3 if needed
        video_path = job.video_path
        s3_video_key = None

        if job.storage_type == "s3" and job.s3_video_key:
            # Video is in S3 - need to download it locally for processing
            s3_video_key = job.s3_video_key
            video_path = str(output_dir / f"input_{job.video_filename}")

        # Start async task
        task = asyncio.create_task(
            self._run_job_async(
                job_id=job.id,
                user_id=job.user_id,
                video_path=video_path,
                s3_video_key=s3_video_key,
                court_boundary=job.court_boundary,
                output_dir=str(output_dir),
                speed_preset=speed_preset,
                background_frame_path=job.background_frame_path,
                save_frame_data=save_frame_data
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
        background_frame_path: str = None,
        s3_video_key: str = None,
        save_frame_data: bool = False
    ):
        """Run analysis job asynchronously."""
        from ..database import SessionLocal

        loop = asyncio.get_event_loop()
        progress_file = Path(output_dir) / "progress.json"
        local_video_path = video_path

        try:
            # Download video from S3 if needed
            if s3_video_key:
                await self._notify_progress(job_id, 2.0, "Downloading video from cloud...")
                local_video_path = await self._download_video_from_s3(
                    s3_key=s3_video_key,
                    local_path=video_path
                )
                logger.info(f"Downloaded video from S3 to: {local_video_path}")

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
                    video_path=local_video_path,
                    court_boundary=court_boundary,
                    output_dir=output_dir,
                    speed_preset=speed_preset,
                    background_frame_path=background_frame_path,
                    save_frame_data=save_frame_data
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
                    storage = get_storage_service()

                    # If using S3, upload outputs and update paths to S3 keys
                    if storage.is_s3():
                        await self._notify_progress(job_id, 96.0, "Uploading results to cloud...")
                        s3_paths = await self._upload_outputs_to_s3(
                            job_id=job_id,
                            user_id=user_id,
                            output_dir=output_dir,
                            result=result
                        )
                        job.report_path = s3_paths.get("report_path")
                        job.annotated_video_path = s3_paths.get("annotated_video_path")
                        job.heatmap_paths = s3_paths.get("heatmap_paths")
                        job.s3_output_prefix = f"{settings.s3_output_prefix}/{job_id}"

                        # Clean up local temp files after S3 upload
                        await self._cleanup_local_output(output_dir)
                    else:
                        # Local storage - use paths as-is
                        job.report_path = result.get("report_path")
                        job.annotated_video_path = result.get("annotated_video_path")
                        # Use heatmap_paths from result (all 4 types), fallback to old single heatmap
                        job.heatmap_paths = result.get("heatmap_paths") or {
                            "movement": result.get("heatmap_image_path")
                        }

                    job.status = JobStatus.COMPLETED
                    job.progress = 100.0
                    job.completed_at = datetime.utcnow()
                    job.status_message = "Analysis complete"
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

            # Clean up cancel flag if it exists
            cancel_flag = Path(output_dir) / "cancel_requested"
            if cancel_flag.exists():
                try:
                    cancel_flag.unlink()
                    logger.info(f"Cleaned up cancel flag for job {job_id}")
                except Exception as e:
                    logger.warning(f"Failed to clean up cancel flag: {e}")

    async def _poll_progress(self, job_id: int, progress_file: str):
        """Poll progress file and update database/WebSocket."""
        from ..database import SessionLocal

        last_progress = 0.0
        last_message = ""

        while True:
            try:
                await asyncio.sleep(2)  # Poll every 2 seconds for faster transcoding updates

                progress_data = AnalyzerService.read_progress_file(progress_file)
                if progress_data:
                    progress = progress_data.get('progress', 0)
                    message = progress_data.get('message', 'Processing...')
                    stage = progress_data.get('stage', '')

                    # Update if progress or message changed
                    if progress > last_progress or message != last_message:
                        last_progress = progress
                        last_message = message

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
                        logger.info(f"Job {job_id} progress: {progress:.1f}% - {message} (stage: {stage})")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling progress for job {job_id}: {e}")

    async def _upload_outputs_to_s3(
        self,
        job_id: int,
        user_id: int,
        output_dir: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upload analysis outputs to S3 and return S3 keys."""
        storage = get_storage_service()
        s3_paths = {}

        output_path = Path(output_dir)

        # Upload report.json
        report_path = result.get("report_path")
        if report_path and Path(report_path).exists():
            s3_key = storage.get_output_path(job_id, "report.json")
            with open(report_path, 'rb') as f:
                storage.outputs.save(s3_key, f, content_type="application/json")
            s3_paths["report_path"] = s3_key
            logger.info(f"Uploaded report to S3: {s3_key}")

        # Upload annotated video
        video_path = result.get("annotated_video_path")
        if video_path and Path(video_path).exists():
            video_filename = Path(video_path).name
            s3_key = storage.get_output_path(job_id, video_filename)
            with open(video_path, 'rb') as f:
                storage.outputs.save(s3_key, f, content_type="video/mp4")
            s3_paths["annotated_video_path"] = s3_key
            logger.info(f"Uploaded annotated video to S3: {s3_key}")

        # Upload heatmaps
        heatmap_paths = result.get("heatmap_paths") or {}
        if not heatmap_paths and result.get("heatmap_image_path"):
            heatmap_paths = {"movement": result.get("heatmap_image_path")}

        s3_heatmap_paths = {}
        for heatmap_type, heatmap_path in heatmap_paths.items():
            if heatmap_path and Path(heatmap_path).exists():
                heatmap_filename = f"heatmap_{heatmap_type}.png"
                s3_key = storage.get_output_path(job_id, heatmap_filename)
                with open(heatmap_path, 'rb') as f:
                    storage.outputs.save(s3_key, f, content_type="image/png")
                s3_heatmap_paths[heatmap_type] = s3_key
                logger.info(f"Uploaded heatmap {heatmap_type} to S3: {s3_key}")

        if s3_heatmap_paths:
            s3_paths["heatmap_paths"] = s3_heatmap_paths

        # Upload frame data for tuning (if exists)
        frame_data_path = result.get("frame_data_path")
        if frame_data_path and Path(frame_data_path).exists():
            frame_data_filename = Path(frame_data_path).name
            s3_key = storage.get_output_path(job_id, frame_data_filename)
            with open(frame_data_path, 'rb') as f:
                storage.outputs.save(s3_key, f, content_type="application/json")
            s3_paths["frame_data_path"] = s3_key
            logger.info(f"Uploaded frame data to S3: {s3_key}")

        return s3_paths

    async def _cleanup_local_output(self, output_dir: str):
        """Clean up local output directory after S3 upload."""
        try:
            output_path = Path(output_dir)
            if output_path.exists():
                shutil.rmtree(output_path)
                logger.info(f"Cleaned up local output directory: {output_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up local output directory {output_dir}: {e}")

    async def _download_video_from_s3(self, s3_key: str, local_path: str) -> str:
        """Download video from S3 to local path for processing."""
        storage = get_storage_service()

        # Ensure parent directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        # Download from S3
        video_data = storage.uploads.load(s3_key)

        # Write to local file
        with open(local_path, 'wb') as f:
            f.write(video_data)

        return local_path

    async def cancel_job(self, db: Session, job: Job) -> bool:
        """Cancel a running job."""
        if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            return False

        # Create cancellation flag file that the worker process will check
        output_dir = settings.output_path / str(job.user_id) / str(job.id)
        cancel_flag = output_dir / "cancel_requested"
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            cancel_flag.touch()
            logger.info(f"Created cancel flag for job {job.id}: {cancel_flag}")
        except Exception as e:
            logger.error(f"Failed to create cancel flag: {e}")

        # Cancel the asyncio task if running
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
