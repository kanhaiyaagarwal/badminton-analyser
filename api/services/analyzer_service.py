"""Service wrapper for CourtBoundedAnalyzer."""

import sys
import json
import subprocess
import os
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Tuple

# Add parent directory to path for importing the analyzer
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from v2_court_bounded_analyzer import CourtBoundedAnalyzer, CourtBoundary
from heatmap_visualizer import HeatmapVisualizer


class AnalyzerService:
    """Service for running badminton analysis."""

    # Codecs that OpenCV can't decode reliably (need transcoding)
    UNSUPPORTED_CODECS = ['av1', 'av01', 'vp9', 'vp09']

    SPEED_PRESETS = {
        "turbo": {
            "process_every_n_frames": 4,
            "processing_width": 320,
            "model_complexity": 0,
            "skip_static_frames": True,
            "skip_video_output": True  # Biggest speedup!
        },
        "fast": {
            "process_every_n_frames": 3,
            "processing_width": 480,
            "model_complexity": 0,
            "skip_static_frames": True,
            "skip_video_output": False
        },
        "balanced": {
            "process_every_n_frames": 2,
            "processing_width": 640,
            "model_complexity": 1,
            "skip_static_frames": True,
            "skip_video_output": False
        },
        "accurate": {
            "process_every_n_frames": 1,
            "processing_width": 960,
            "model_complexity": 1,
            "skip_static_frames": False,
            "skip_video_output": False
        }
    }

    @staticmethod
    def create_court_boundary(boundary_data: Dict[str, Any]) -> CourtBoundary:
        """Create CourtBoundary from dictionary data."""
        return CourtBoundary(
            top_left=tuple(boundary_data["top_left"]),
            top_right=tuple(boundary_data["top_right"]),
            bottom_left=tuple(boundary_data["bottom_left"]),
            bottom_right=tuple(boundary_data["bottom_right"]),
            court_color=boundary_data.get("court_color", "green")
        )

    @staticmethod
    def _get_video_codec(video_path: str) -> Optional[str]:
        """Get video codec name using ffprobe."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.strip().lower()
        except Exception as e:
            logger.warning(f"Failed to detect codec: {e}")
        return None

    @staticmethod
    def _needs_transcoding(video_path: str) -> bool:
        """Check if video needs transcoding (unsupported codec)."""
        codec = AnalyzerService._get_video_codec(video_path)
        if codec:
            return codec in AnalyzerService.UNSUPPORTED_CODECS
        return False

    @staticmethod
    def _get_video_duration(video_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to get video duration: {e}")
        return 0.0

    @staticmethod
    def _write_progress(progress_file: Optional[str], progress: float, message: str, stage: str = ""):
        """Write progress to file for external monitoring."""
        if not progress_file:
            return
        try:
            with open(progress_file, 'w') as f:
                json.dump({
                    "progress": progress,
                    "message": message,
                    "stage": stage,
                    "timestamp": time.time()
                }, f)
        except Exception as e:
            logger.warning(f"Failed to write progress: {e}")

    # Transcode settings per speed preset
    TRANSCODE_SETTINGS = {
        "turbo": {"max_height": 720, "preset": "ultrafast", "crf": 28, "threads": 2},
        "fast": {"max_height": 720, "preset": "veryfast", "crf": 26, "threads": 2},
        "balanced": {"max_height": 1080, "preset": "fast", "crf": 23, "threads": 2},
        "accurate": {"max_height": None, "preset": "fast", "crf": 20, "threads": 4},  # None = keep original
    }

    @staticmethod
    def _check_cancelled(output_dir: Path) -> bool:
        """Check if job was cancelled by looking for cancel flag file."""
        cancel_flag = output_dir / "cancel_requested"
        return cancel_flag.exists()

    @staticmethod
    def _reencode_to_h264(input_path: str, output_dir: Path = None) -> Optional[str]:
        """
        Re-encode a video from mp4v to browser-compatible H.264.

        OpenCV's VideoWriter uses mp4v codec which browsers don't support.
        This function re-encodes to H.264 for browser playback.

        Args:
            input_path: Path to the mp4v encoded video
            output_dir: Optional output directory (defaults to same as input)

        Returns:
            Path to the H.264 encoded video, or None if failed
        """
        if not input_path or not Path(input_path).exists():
            return None

        input_path = Path(input_path)
        if output_dir is None:
            output_dir = input_path.parent

        # Create temporary output path
        temp_output = output_dir / f"_h264_{input_path.name}"

        try:
            cmd = [
                'ffmpeg', '-y',
                '-loglevel', 'warning',
                '-i', str(input_path),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',  # Ensure browser compatibility
                '-movflags', '+faststart',  # Enable progressive download
                str(temp_output)
            ]

            logger.info(f"Re-encoding annotated video to H.264: {input_path.name}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                logger.error(f"H.264 re-encoding failed: {result.stderr}")
                return None

            # Replace original with H.264 version
            input_path.unlink()
            temp_output.rename(input_path)
            logger.info(f"Successfully re-encoded to H.264: {input_path.name}")
            return str(input_path)

        except subprocess.TimeoutExpired:
            logger.error("H.264 re-encoding timed out")
            if temp_output.exists():
                temp_output.unlink()
            return None
        except Exception as e:
            logger.error(f"H.264 re-encoding error: {e}")
            if temp_output.exists():
                temp_output.unlink()
            return None

    @staticmethod
    def _scale_court_boundary(boundary: Dict[str, Any], scale_factor: float) -> Dict[str, Any]:
        """Scale court boundary coordinates when video is downscaled."""
        scaled = {}
        for key, value in boundary.items():
            if key in ["top_left", "top_right", "bottom_left", "bottom_right"]:
                # Scale x and y coordinates
                scaled[key] = [int(value[0] * scale_factor), int(value[1] * scale_factor)]
            else:
                # Keep other fields (like court_color) as is
                scaled[key] = value
        return scaled

    @staticmethod
    def _transcode_video(
        input_path: str,
        output_path: str,
        progress_file: Optional[str] = None,
        speed_preset: str = "balanced",
        output_dir: Optional[Path] = None
    ) -> bool:
        """
        Transcode video to H.264 for OpenCV compatibility.

        Args:
            input_path: Path to input video
            output_path: Path for transcoded output
            progress_file: Optional path to write progress updates
            speed_preset: Speed preset to determine quality/resolution

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get transcode settings based on speed preset
            settings = AnalyzerService.TRANSCODE_SETTINGS.get(
                speed_preset,
                AnalyzerService.TRANSCODE_SETTINGS["balanced"]
            )
            max_height = settings["max_height"]
            preset = settings["preset"]
            crf = settings["crf"]
            threads = settings["threads"]

            logger.info(f"Transcoding video to H.264: {input_path}")
            logger.info(f"Transcode settings: max_height={max_height}, preset={preset}, crf={crf}, threads={threads}")

            # Get video duration for progress calculation
            duration = AnalyzerService._get_video_duration(input_path)
            logger.info(f"Video duration: {duration:.1f}s")

            # Write initial progress
            AnalyzerService._write_progress(progress_file, 0, "Transcoding video...", "transcode")

            # Build ffmpeg command
            cmd = [
                'ffmpeg', '-y',
                '-loglevel', 'warning',  # Reduce stderr output to prevent buffer deadlock
                '-i', input_path,
                '-c:v', 'libx264',
                '-preset', preset,
                '-crf', str(crf),
                '-threads', str(threads),  # Limit CPU usage
            ]

            # Add scale filter if max_height specified (downscale to save time)
            if max_height:
                # Scale to max_height while maintaining aspect ratio, only if larger
                # -2 ensures width is divisible by 2 (required for h264)
                cmd.extend(['-vf', f'scale=-2:min({max_height}\\,ih)'])
                logger.info(f"Downscaling to max {max_height}p")

            cmd.extend([
                '-an',  # Remove audio - not needed for analysis, saves time
                '-movflags', '+faststart',
                '-progress', 'pipe:1',  # Output progress to stdout
                output_path
            ])
            logger.info("Audio track will be removed (not needed for analysis)")

            # Run with progress monitoring
            # IMPORTANT: Use DEVNULL for stderr to prevent deadlock
            # If we pipe stderr but don't read it, the buffer fills up and ffmpeg blocks
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # Discard stderr to prevent deadlock
                universal_newlines=True
            )

            last_progress_time = time.time()
            last_progress_value = 0
            stall_warning_shown = False
            cancelled = False

            while process.poll() is None:
                # Check for cancellation every iteration
                if output_dir and AnalyzerService._check_cancelled(output_dir):
                    logger.info("Transcoding cancelled by user, terminating ffmpeg...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    cancelled = True
                    break

                line = process.stdout.readline()
                if line and duration > 0:
                    # Parse ffmpeg progress output
                    if line.startswith('out_time_ms='):
                        try:
                            time_ms = int(line.split('=')[1])
                            time_s = time_ms / 1000000
                            progress = min(95, (time_s / duration) * 100)
                            last_progress_value = progress
                            stall_warning_shown = False

                            # Update progress every 2 seconds
                            if time.time() - last_progress_time > 2:
                                AnalyzerService._write_progress(
                                    progress_file,
                                    progress,
                                    f"Transcoding: {progress:.0f}%",
                                    "transcode"
                                )
                                logger.info(f"Transcoding progress: {progress:.1f}%")
                                last_progress_time = time.time()
                        except (ValueError, IndexError):
                            pass

                # Stall detection: warn if no progress for 60 seconds
                if time.time() - last_progress_time > 60 and not stall_warning_shown:
                    logger.warning(f"Transcoding may be stalled at {last_progress_value:.1f}% - no progress for 60s")
                    stall_warning_shown = True

            if cancelled:
                # Clean up partial output file
                if Path(output_path).exists():
                    Path(output_path).unlink()
                return False

            # Wait for completion (stderr already discarded)
            try:
                process.wait(timeout=1800)
            except subprocess.TimeoutExpired:
                logger.error("Transcoding timed out after 30 minutes")
                process.kill()
                return False

            if process.returncode == 0:
                logger.info(f"Transcoding complete: {output_path}")
                AnalyzerService._write_progress(progress_file, 100, "Transcoding complete", "transcode")
                return True
            else:
                logger.error(f"Transcoding failed with return code: {process.returncode}")
                return False
        except Exception as e:
            logger.error(f"Transcoding error: {e}")
            return False

    @staticmethod
    def run_analysis(
        video_path: str,
        court_boundary: Dict[str, Any],
        output_dir: Path,
        speed_preset: str = "balanced",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        background_frame_path: Optional[str] = None,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: Optional[float] = None,
        save_frame_data: bool = False
    ) -> Dict[str, Any]:
        """
        Run video analysis.

        Args:
            video_path: Path to video file
            court_boundary: Court boundary dictionary
            output_dir: Directory for output files
            speed_preset: Speed preset (fast, balanced, accurate)
            progress_callback: Optional callback for progress updates (progress%, message)
            background_frame_path: Optional path to background frame for heatmaps
            velocity_thresholds: Optional custom velocity thresholds for shot detection
            position_thresholds: Optional custom position thresholds for shot detection
            shot_cooldown_seconds: Optional custom shot cooldown period
            save_frame_data: Whether to save per-frame data for tuning

        Returns:
            Analysis report dictionary
        """
        # Get preset settings
        preset = AnalyzerService.SPEED_PRESETS.get(speed_preset, AnalyzerService.SPEED_PRESETS["balanced"])

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Set progress file for external monitoring
        progress_file = output_dir / "progress.json"

        # Check if video needs transcoding (AV1, VP9, etc.)
        transcoded_path = None
        analysis_video_path = video_path
        scale_factor = 1.0  # For scaling court boundary if video is downscaled

        if AnalyzerService._needs_transcoding(video_path):
            codec = AnalyzerService._get_video_codec(video_path)
            logger.info(f"Video uses unsupported codec ({codec}), transcoding to H.264...")

            # Get original video dimensions for scaling court boundary (use ffprobe for AV1)
            original_info = AnalyzerService._get_video_info_ffprobe(video_path)
            if not original_info:
                original_info = AnalyzerService.get_video_info(video_path)
            original_height = original_info.get("height", 1080) if original_info else 1080
            original_width = original_info.get("width", 1920) if original_info else 1920
            logger.info(f"Original video dimensions: {original_width}x{original_height}")

            transcoded_path = str(output_dir / f"_transcoded_{Path(video_path).stem}.mp4")
            if AnalyzerService._transcode_video(video_path, transcoded_path, str(progress_file), speed_preset, output_dir):
                analysis_video_path = transcoded_path
                logger.info("Transcoding successful, proceeding with analysis")

                # Get transcoded video dimensions and calculate scale factor
                transcoded_info = AnalyzerService.get_video_info(transcoded_path)
                if transcoded_info:
                    transcoded_height = transcoded_info.get("height", original_height)
                    transcoded_width = transcoded_info.get("width", original_width)
                    logger.info(f"Transcoded video dimensions: {transcoded_width}x{transcoded_height}")

                    if transcoded_height != original_height:
                        scale_factor = transcoded_height / original_height
                        logger.info(f"Video downscaled: {original_height}p -> {transcoded_height}p, scale_factor={scale_factor:.3f}")
                    else:
                        logger.info("No scaling needed - dimensions unchanged")
                else:
                    logger.warning("Could not get transcoded video info, skipping boundary scaling")
            else:
                # Check if it was cancelled
                if AnalyzerService._check_cancelled(output_dir):
                    logger.info("Job was cancelled during transcoding")
                    raise Exception("Job cancelled by user")
                logger.warning("Transcoding failed, attempting analysis with original file...")

        # Scale court boundary if video was downscaled
        scaled_boundary = court_boundary
        if scale_factor != 1.0:
            logger.info(f"Scaling court boundary by factor {scale_factor:.3f}")
            logger.info(f"Original boundary: top_left={court_boundary.get('top_left')}, bottom_right={court_boundary.get('bottom_right')}")
            scaled_boundary = AnalyzerService._scale_court_boundary(court_boundary, scale_factor)
            logger.info(f"Scaled boundary: top_left={scaled_boundary.get('top_left')}, bottom_right={scaled_boundary.get('bottom_right')}")
        else:
            logger.info("Using original court boundary (no scaling needed)")

        # Create court boundary
        court = AnalyzerService.create_court_boundary(scaled_boundary)

        # Get video FPS for time-based velocity calculations
        import cv2
        cap = cv2.VideoCapture(analysis_video_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 30.0
        cap.release()

        # Calculate effective FPS (accounts for frame skipping)
        effective_fps = video_fps / preset["process_every_n_frames"]
        logger.info(f"Video FPS: {video_fps:.1f}, effective FPS: {effective_fps:.1f} (every {preset['process_every_n_frames']} frames)")

        # Prepare analyzer kwargs with optional thresholds
        analyzer_kwargs = {
            "court_boundary": court,
            "process_every_n_frames": preset["process_every_n_frames"],
            "processing_width": preset["processing_width"],
            "model_complexity": preset["model_complexity"],
            "skip_static_frames": preset["skip_static_frames"],
            "effective_fps": effective_fps,
        }

        # Add custom thresholds if provided
        if velocity_thresholds:
            analyzer_kwargs["velocity_thresholds"] = velocity_thresholds
            logger.info(f"Using custom velocity thresholds: {velocity_thresholds}")
        if position_thresholds:
            analyzer_kwargs["position_thresholds"] = position_thresholds
            logger.info(f"Using custom position thresholds: {position_thresholds}")
        if shot_cooldown_seconds is not None:
            analyzer_kwargs["shot_cooldown_seconds"] = shot_cooldown_seconds
            logger.info(f"Using custom shot cooldown: {shot_cooldown_seconds}s")

        # Create analyzer with effective FPS for time-based velocity
        analyzer = CourtBoundedAnalyzer(**analyzer_kwargs)

        # Set progress file for external monitoring
        analyzer.progress_file = str(progress_file)

        # Set cancel flag path so analyzer can check for cancellation
        cancel_flag_path = output_dir / "cancel_requested"
        analyzer.cancel_flag_path = str(cancel_flag_path)

        # Output paths
        video_name = Path(video_path).stem

        # Skip video output for turbo mode (major speedup)
        skip_video = preset.get("skip_video_output", False)
        annotated_video_path = None if skip_video else str(output_dir / f"analyzed_{video_name}.mp4")

        # Run analysis (use transcoded path if available)
        # Pass save_frame_data to capture frame data during main pass (avoids inconsistent second pass)
        report = analyzer.analyze_video(
            video_path=analysis_video_path,
            output_path=annotated_video_path,
            show_live=False,
            save_frame_data=save_frame_data
        )

        # Save report
        report_path = str(output_dir / f"report_{video_name}.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Add paths to report
        report["report_path"] = report_path
        report["annotated_video_path"] = annotated_video_path

        # Note: Annotated video uses mp4v codec (not browser-compatible)
        # Re-encoding to H.264 is done on-demand in the tuning router when requested

        # If video was transcoded, extract background frame from transcoded video
        # (original background_frame_path is from 4K, but analysis ran on 720p)
        actual_background_frame = background_frame_path
        if transcoded_path and Path(transcoded_path).exists():
            transcoded_bg_path = str(output_dir / "background_frame_transcoded.png")
            if AnalyzerService.save_frame_to_file(transcoded_path, transcoded_bg_path, timestamp=0.0):
                actual_background_frame = transcoded_bg_path
                logger.info(f"Using background frame from transcoded video: {transcoded_bg_path}")

        # Generate all heatmap visualizations
        heatmap_data_path = report.get("heatmap_data_path")
        if heatmap_data_path and Path(heatmap_data_path).exists():
            heatmap_paths = AnalyzerService.generate_all_heatmaps(
                heatmap_data_path, output_dir, actual_background_frame
            )
            report["heatmap_paths"] = heatmap_paths

        # Save frame data for tuning if requested (already captured during main pass)
        if save_frame_data and 'tuning_frame_data' in report:
            try:
                frame_data_path = str(output_dir / f"frame_data_{video_name}.json")
                with open(frame_data_path, 'w') as f:
                    json.dump(report['tuning_frame_data'], f, indent=2)
                report["frame_data_path"] = frame_data_path
                logger.info(f"Frame data saved for tuning: {frame_data_path} ({len(report['tuning_frame_data'].get('frames', []))} frames)")
                # Remove from report to save memory (data is in file now)
                del report['tuning_frame_data']
            except Exception as e:
                logger.warning(f"Failed to save frame data for tuning: {e}")

        # Store thresholds used in report
        report["thresholds_used"] = analyzer.get_current_thresholds()
        report["cooldown_seconds"] = analyzer.get_cooldown_seconds()

        # Clean up progress file
        if progress_file.exists():
            progress_file.unlink()

        # Clean up transcoded file
        if transcoded_path and Path(transcoded_path).exists():
            try:
                Path(transcoded_path).unlink()
                logger.debug(f"Cleaned up transcoded file: {transcoded_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up transcoded file: {e}")

        return report

    @staticmethod
    def generate_all_heatmaps(data_path: str, output_dir: Path, background_frame_path: str = None) -> Dict[str, str]:
        """
        Generate all 4 heatmap visualization types.

        Args:
            data_path: Path to heatmap data JSON
            output_dir: Directory to save images
            background_frame_path: Optional path to video frame for realistic background

        Returns:
            Dictionary mapping heatmap type to file path
        """
        try:
            visualizer = HeatmapVisualizer(data_path, background_frame_path=background_frame_path)

            heatmap_paths = {}

            # Generate each visualization type
            visualizations = {
                'rally_heatmap': visualizer.create_rally_colored_heatmap(),
                'trajectory': visualizer.create_trajectory_plot(),
                'time_gradient': visualizer.create_time_gradient_plot(),
                'density_contour': visualizer.create_density_contour(),
            }

            import cv2
            for name, image in visualizations.items():
                path = output_dir / f"{name}.png"
                cv2.imwrite(str(path), image)
                heatmap_paths[name] = str(path)

            return heatmap_paths
        except Exception as e:
            logger.error(f"Error generating heatmaps: {e}")
            return {}

    @staticmethod
    def extract_frame(video_path: str, timestamp: float = 0.0) -> Optional[bytes]:
        """
        Extract a frame from video at given timestamp.

        Args:
            video_path: Path to video file
            timestamp: Timestamp in seconds

        Returns:
            JPEG encoded frame bytes or None
        """
        import cv2

        # First try OpenCV
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            try:
                # Seek to timestamp
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ret, frame = cap.read()

                if ret and frame is not None:
                    # Encode as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    return buffer.tobytes()
            finally:
                cap.release()

        # Fallback to ffmpeg for unsupported codecs (AV1, etc.)
        return AnalyzerService._extract_frame_ffmpeg(video_path, timestamp)

    @staticmethod
    def _extract_frame_ffmpeg(video_path: str, timestamp: float = 0.0) -> Optional[bytes]:
        """
        Extract a frame using ffmpeg subprocess (fallback for unsupported codecs).
        """
        import subprocess
        import tempfile
        import os

        try:
            # Create temp file for the frame
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name

            # Use ffmpeg to extract frame
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                tmp_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=30)

            if result.returncode == 0 and os.path.exists(tmp_path):
                with open(tmp_path, 'rb') as f:
                    frame_bytes = f.read()
                os.unlink(tmp_path)
                return frame_bytes if len(frame_bytes) > 0 else None

            # Clean up on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return None

        except Exception as e:
            logger.warning(f"ffmpeg frame extraction failed: {e}")
            return None

    @staticmethod
    def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
        """Get video metadata."""
        import cv2

        # Try OpenCV first
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            try:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                if width > 0 and height > 0 and fps > 0:
                    return {
                        "width": width,
                        "height": height,
                        "fps": fps,
                        "frame_count": frame_count,
                        "duration": frame_count / fps if fps > 0 else 0
                    }
            finally:
                cap.release()

        # Fallback to ffprobe for unsupported codecs
        return AnalyzerService._get_video_info_ffprobe(video_path)

    @staticmethod
    def _get_video_info_ffprobe(video_path: str) -> Optional[Dict[str, Any]]:
        """Get video info using ffprobe (fallback for unsupported codecs)."""
        import subprocess
        import json as json_module

        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-select_streams', 'v:0',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json_module.loads(result.stdout)
                if data.get('streams'):
                    stream = data['streams'][0]
                    # Parse frame rate (can be "30/1" or "29.97")
                    fps_str = stream.get('r_frame_rate', '30/1')
                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        fps = float(num) / float(den) if float(den) > 0 else 30.0
                    else:
                        fps = float(fps_str)

                    width = int(stream.get('width', 0))
                    height = int(stream.get('height', 0))
                    frame_count = int(stream.get('nb_frames', 0))

                    # If frame count not available, calculate from duration
                    if frame_count == 0:
                        duration = float(stream.get('duration', 0))
                        frame_count = int(duration * fps) if duration > 0 else 0
                    else:
                        duration = frame_count / fps if fps > 0 else 0

                    return {
                        "width": width,
                        "height": height,
                        "fps": fps,
                        "frame_count": frame_count,
                        "duration": duration
                    }
            return None
        except Exception as e:
            logger.warning(f"ffprobe failed: {e}")
            return None

    @staticmethod
    def save_frame_to_file(video_path: str, output_path: str, timestamp: float = 0.0) -> bool:
        """
        Extract and save a frame from video to a file.

        Args:
            video_path: Path to video file
            output_path: Path to save the frame
            timestamp: Timestamp in seconds

        Returns:
            True if successful, False otherwise
        """
        import cv2

        # Try OpenCV first
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            try:
                # Seek to timestamp
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ret, frame = cap.read()

                if ret and frame is not None:
                    # Save as PNG for better quality (used for heatmap background)
                    cv2.imwrite(output_path, frame)
                    return True
            finally:
                cap.release()

        # Fallback to ffmpeg for unsupported codecs
        return AnalyzerService._save_frame_ffmpeg(video_path, output_path, timestamp)

    @staticmethod
    def _save_frame_ffmpeg(video_path: str, output_path: str, timestamp: float = 0.0) -> bool:
        """Save a frame using ffmpeg subprocess (fallback for unsupported codecs)."""
        import subprocess

        try:
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '1',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=30)
            return result.returncode == 0

        except Exception as e:
            logger.warning(f"ffmpeg frame save failed: {e}")
            return False

    @staticmethod
    def read_progress_file(progress_file_path: str) -> Optional[Dict[str, Any]]:
        """Read progress from a progress JSON file."""
        try:
            if Path(progress_file_path).exists():
                with open(progress_file_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
