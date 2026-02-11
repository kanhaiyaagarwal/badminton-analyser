"""Read video frames and yield base64-encoded JPEGs."""

import base64
from typing import Generator, Tuple

import cv2


class VideoFrameReader:
    def __init__(self, video_path: str, jpeg_quality: int = 80):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {video_path}")
        self.jpeg_quality = jpeg_quality

    @property
    def native_fps(self) -> float:
        return self.cap.get(cv2.CAP_PROP_FPS)

    @property
    def total_frames(self) -> int:
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def width(self) -> int:
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def get_full_frame_court(self) -> dict:
        """Return court boundary covering the entire frame."""
        w, h = self.width, self.height
        return {
            "top_left": [0, 0],
            "top_right": [w, 0],
            "bottom_left": [0, h],
            "bottom_right": [w, h],
        }

    def frames(
        self,
        target_fps: int,
        max_frames: int = 0,
        start_frame: int = 0,
    ) -> Generator[Tuple[str, float, int, int, int], None, None]:
        """
        Yield (base64_jpeg, timestamp, width, height, frame_idx) tuples.

        Subsamples to target_fps from the native video FPS.
        """
        native = self.native_fps
        if native <= 0:
            native = 30.0
        step = max(1, round(native / target_fps))

        if start_frame > 0:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frame_idx = start_frame
        yielded = 0
        while True:
            if max_frames > 0 and yielded >= max_frames:
                break

            ret, frame = self.cap.read()
            if not ret:
                break

            if (frame_idx - start_frame) % step == 0:
                ok, buf = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                )
                if ok:
                    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
                    timestamp = frame_idx / native
                    yield b64, timestamp, self.width, self.height, frame_idx
                    yielded += 1

            frame_idx += 1

    def close(self):
        self.cap.release()
