"""
Shuttle tracker using TrackNetV2 for shuttlecock detection.

Detection only — no classification, no video writing.
Provides both standalone video processing and per-frame detection
for integration into the main analysis frame loop.
"""

import logging
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

TRACKNET_INPUT_H = 288
TRACKNET_INPUT_W = 512
WEIGHTS_URL = "https://github.com/ChgygLin/TrackNetV2-pytorch/raw/main/tf2torch/track.pt"

# Default weights location (project root / weights / track.pt)
DEFAULT_WEIGHTS_PATH = Path(__file__).parent.parent / "weights" / "track.pt"


class ShuttleTracker:
    """Detects shuttlecock positions using TrackNetV2.

    Two usage modes:
    1. Standalone: detect_in_video() processes an entire video
    2. Frame loop: detect_in_frame() called per-frame from a combined loop
    """

    def __init__(self, weights_path: Optional[str] = None, device: str = "auto"):
        """
        Args:
            weights_path: Path to track.pt weights. Uses default location if None.
            device: "auto", "cuda", "mps", or "cpu".
        """
        import torch
        import torchvision.transforms as T

        if device == "auto":
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)

        if weights_path is None:
            weights_path = str(DEFAULT_WEIGHTS_PATH)

        if not Path(weights_path).exists():
            weights_path = self._download_weights(weights_path)

        from shuttle_tracking.tracknet_model import TrackNet

        self.model = TrackNet()
        checkpoint = torch.load(weights_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(checkpoint)
        self.model.to(self.device)
        self.model.eval()

        self.transform = T.ToTensor()
        self._torch = torch

        logger.info(f"ShuttleTracker loaded on {self.device}")

    @staticmethod
    def _download_weights(target_path: str) -> str:
        """Download track.pt weights if not present."""
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            logger.info(f"Downloading TrackNetV2 weights to {target}...")
            urllib.request.urlretrieve(WEIGHTS_URL, str(target))
            logger.info("Download complete.")
        return str(target)

    def _preprocess_frames(self, frames: List[np.ndarray]):
        """Resize, normalize, and concatenate 3 frames into model input tensor.

        Args:
            frames: List of 3 BGR frames (numpy arrays).

        Returns:
            Tensor of shape [1, 9, 288, 512].
        """
        import torch

        tensors = []
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb, (TRACKNET_INPUT_W, TRACKNET_INPUT_H))
            tensor = self.transform(resized)  # [3, 288, 512], 0-1
            tensors.append(tensor)
        concatenated = torch.cat(tensors, dim=0)  # [9, 288, 512]
        return concatenated.unsqueeze(0)  # [1, 9, 288, 512]

    def _extract_position(self, heatmap, orig_w: int, orig_h: int) -> Tuple[bool, int, int, float]:
        """Extract shuttle position from a single heatmap.

        Args:
            heatmap: Tensor of shape [288, 512], values 0-1.
            orig_w: Original frame width.
            orig_h: Original frame height.

        Returns:
            (visible, x, y, confidence) where visible is bool,
            x/y are in original frame coordinates, confidence is peak value.
        """
        confidence = float(heatmap.max())
        binary = (heatmap.cpu().numpy() > 0.5).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return False, 0, 0, confidence

        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        cx = x + w / 2
        cy = y + h / 2

        # Scale to original resolution
        scale_x = orig_w / TRACKNET_INPUT_W
        scale_y = orig_h / TRACKNET_INPUT_H
        ox = int(cx * scale_x)
        oy = int(cy * scale_y)

        return True, ox, oy, confidence

    def detect_in_frame(self, frame_buffer: List[np.ndarray]) -> Tuple[bool, int, int, float]:
        """Detect shuttle from a 3-frame buffer. For use in combined frame loop.

        Args:
            frame_buffer: List of exactly 3 BGR frames (sliding window).

        Returns:
            (visible, x, y, confidence) tuple.
        """
        if len(frame_buffer) != 3:
            return False, 0, 0, 0.0

        orig_h, orig_w = frame_buffer[2].shape[:2]

        input_tensor = self._preprocess_frames(frame_buffer).to(self.device)

        with self._torch.no_grad():
            output = self.model(input_tensor)  # [1, 3, 288, 512]

        # Extract position from the last heatmap (corresponds to latest frame)
        heatmap = output[0, 2]  # [288, 512]
        return self._extract_position(heatmap, orig_w, orig_h)

    def detect_in_video(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[dict]:
        """Process entire video and return per-frame shuttle detections.

        Args:
            video_path: Path to input video.
            progress_callback: Optional (progress_pct, message) callback.
            cancel_check: Optional callable returning True to cancel.

        Returns:
            List of dicts: {frame, timestamp, x, y, confidence, visible} per frame.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        detections = []
        frame_buffer = []
        frame_idx = 0
        detection_count = 0

        # Read initial 3 frames
        for _ in range(3):
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return detections
            frame_buffer.append(frame)

        try:
            while True:
                if cancel_check and cancel_check():
                    logger.info("Shuttle detection cancelled")
                    break

                visible, x, y, confidence = self.detect_in_frame(frame_buffer)

                if visible:
                    detection_count += 1

                timestamp = frame_idx / fps if fps > 0 else 0.0
                detections.append({
                    "frame": frame_idx,
                    "timestamp": round(timestamp, 4),
                    "x": x if visible else -1,
                    "y": y if visible else -1,
                    "confidence": round(confidence, 4),
                    "visible": visible,
                })

                frame_idx += 1

                # Progress
                if progress_callback and frame_idx % 100 == 0:
                    pct = (frame_idx / total_frames) * 100 if total_frames > 0 else 0
                    rate = detection_count / frame_idx * 100 if frame_idx > 0 else 0
                    progress_callback(
                        pct,
                        f"Shuttle tracking: {frame_idx}/{total_frames} ({rate:.1f}% detection)"
                    )

                # Slide window
                ret, next_frame = cap.read()
                if not ret:
                    break
                frame_buffer.pop(0)
                frame_buffer.append(next_frame)

        finally:
            cap.release()

        logger.info(
            f"Shuttle tracking complete: {detection_count}/{frame_idx} detections "
            f"({detection_count / frame_idx * 100:.1f}%)" if frame_idx > 0 else
            "Shuttle tracking complete: no frames processed"
        )

        return detections
