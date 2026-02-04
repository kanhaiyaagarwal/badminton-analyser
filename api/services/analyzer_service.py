"""Service wrapper for CourtBoundedAnalyzer."""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Add parent directory to path for importing the analyzer
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from v2_court_bounded_analyzer import CourtBoundedAnalyzer, CourtBoundary
from heatmap_visualizer import HeatmapVisualizer


class AnalyzerService:
    """Service for running badminton analysis."""

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
    def run_analysis(
        video_path: str,
        court_boundary: Dict[str, Any],
        output_dir: Path,
        speed_preset: str = "balanced",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        background_frame_path: Optional[str] = None
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

        Returns:
            Analysis report dictionary
        """
        # Get preset settings
        preset = AnalyzerService.SPEED_PRESETS.get(speed_preset, AnalyzerService.SPEED_PRESETS["balanced"])

        # Create court boundary
        court = AnalyzerService.create_court_boundary(court_boundary)

        # Create analyzer
        analyzer = CourtBoundedAnalyzer(
            court_boundary=court,
            process_every_n_frames=preset["process_every_n_frames"],
            processing_width=preset["processing_width"],
            model_complexity=preset["model_complexity"],
            skip_static_frames=preset["skip_static_frames"]
        )

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Set progress file for external monitoring
        progress_file = output_dir / "progress.json"
        analyzer.progress_file = str(progress_file)

        # Output paths
        video_name = Path(video_path).stem

        # Skip video output for turbo mode (major speedup)
        skip_video = preset.get("skip_video_output", False)
        annotated_video_path = None if skip_video else str(output_dir / f"analyzed_{video_name}.mp4")

        # Run analysis
        report = analyzer.analyze_video(
            video_path=video_path,
            output_path=annotated_video_path,
            show_live=False
        )

        # Save report
        report_path = str(output_dir / f"report_{video_name}.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Add paths to report
        report["report_path"] = report_path
        report["annotated_video_path"] = annotated_video_path

        # Generate all heatmap visualizations
        heatmap_data_path = report.get("heatmap_data_path")
        if heatmap_data_path and Path(heatmap_data_path).exists():
            heatmap_paths = AnalyzerService.generate_all_heatmaps(
                heatmap_data_path, output_dir, background_frame_path
            )
            report["heatmap_paths"] = heatmap_paths

        # Clean up progress file
        if progress_file.exists():
            progress_file.unlink()

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
            print(f"Error generating heatmaps: {e}")
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
            print(f"ffmpeg frame extraction failed: {e}")
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
            print(f"ffprobe failed: {e}")
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
            print(f"ffmpeg frame save failed: {e}")
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
