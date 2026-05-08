"""
video_capture.py — Thread-safe OpenCV webcam reader with a rolling frame buffer.

Design decisions:
  - Background thread reads frames continuously so the main thread is never blocked.
  - A deque buffer keeps the last N seconds of raw frames for clip recording.
  - get_frame() always returns the most recent frame (or None if not started).
  - get_buffer() returns a snapshot of the current buffer for clip saving.
  - The webcam device path is configurable via settings.camera_index.
  - Falls back gracefully if the webcam is not available (e.g. in CI/testing).
"""
import cv2
import threading
import time
import logging
from collections import deque
from typing import Optional
import numpy as np
from app.config import settings

logger = logging.getLogger(__name__)


class VideoCapture:
    """
    Thread-safe webcam reader.

    Usage:
        video_capture.start()           # call once at startup (lifespan)
        frame = video_capture.get_frame()
        video_capture.stop()            # call on shutdown
    """

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._is_video_file: bool = False  # True if playing a video file (vs live camera)
        self._frame_delay_ms: float = 0.0  # Delay between frames for video files
        # Rolling buffer: stores (timestamp, frame) tuples
        # maxlen = fps × pre-roll seconds  → e.g. 30fps × 10s = 300 frames
        self._buffer: deque = deque(
            maxlen=settings.camera_fps * settings.clip_pre_seconds
        )
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_frame_time: float = 0.0
        self._frame_count: int = 0
        self._error: Optional[str] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, video_file: Optional[str] = None) -> bool:
        """
        Open a video source (camera or file) and start the background reader thread.
        
        Args:
            video_file: Path to video file. If None, uses camera_index from settings.
        
        Returns True if the source opened successfully.
        """
        if self._running:
            logger.warning("VideoCapture already running")
            return True

        if video_file:
            logger.info(f"Opening video file: {video_file}")
            self.cap = cv2.VideoCapture(video_file)
            self._is_video_file = True
            if not self.cap.isOpened():
                self._error = f"Cannot open video file: {video_file}"
                logger.error(self._error)
                return False
            
            # Get FPS from video file and calculate frame delay
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # Default fallback
            self._frame_delay_ms = 1000.0 / fps  # Convert to milliseconds
            logger.info(f"Video FPS: {fps:.1f}, frame delay: {self._frame_delay_ms:.1f}ms")
        else:
            logger.info(
                f"Opening camera index={settings.camera_index} "
                f"{settings.camera_width}x{settings.camera_height} @ {settings.camera_fps}fps"
            )
            self.cap = cv2.VideoCapture(settings.camera_index)
            self._is_video_file = False

            if not self.cap.isOpened():
                self._error = f"Cannot open camera index {settings.camera_index}"
                logger.error(self._error)
                return False

            # Apply camera settings (only for camera, not video files)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  settings.camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_height)
            self.cap.set(cv2.CAP_PROP_FPS,          settings.camera_fps)
            # Reduce buffer so we always get a fresh frame
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._running = True
        self._thread = threading.Thread(
            target=self._reader_loop,
            name="video-capture",
            daemon=True,          # thread dies when main process exits
        )
        self._thread.start()
        logger.info("VideoCapture thread started")
        return True

    def get_frame(self) -> Optional[np.ndarray]:
        """Return the most recent frame (BGR numpy array) or None."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def get_buffer(self) -> list:
        """
        Return a snapshot of the rolling buffer as a list of (timestamp, frame) tuples.
        Used by clip_recorder to save pre-fall footage.
        """
        with self._lock:
            return list(self._buffer)

    def stop(self):
        """Stop the reader thread and release the camera."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("VideoCapture stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps_actual(self) -> float:
        """Actual FPS computed from frame count (useful for debugging)."""
        return self.cap.get(cv2.CAP_PROP_FPS) if self.cap else 0.0

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def frame_count(self) -> int:
        return self._frame_count

    # ── Background reader ─────────────────────────────────────────────────────

    def _reader_loop(self):
        """
        Runs in background thread.
        Reads frames as fast as the camera produces them and stores
        the latest one in self._frame + appends to the rolling buffer.
        """
        consecutive_failures = 0
        max_failures = 30  # after 30 consecutive failures, give up

        while self._running:
            if self.cap is None or not self.cap.isOpened():
                logger.error("Camera disconnected, stopping reader loop")
                self._error = "Camera disconnected"
                self._running = False
                break

            ret, frame = self.cap.read()

            if not ret or frame is None:
                consecutive_failures += 1
                logger.warning(
                    f"Frame read failed ({consecutive_failures}/{max_failures})"
                )
                if consecutive_failures >= max_failures:
                    logger.error("Too many consecutive read failures, stopping")
                    self._error = "Camera read failure"
                    self._running = False
                    break
                time.sleep(0.05)
                continue

            consecutive_failures = 0
            now = time.time()

            with self._lock:
                self._frame = frame
                self._buffer.append((now, frame.copy()))
                self._last_frame_time = now
                self._frame_count += 1
            
            # For video files, throttle playback to match the video's FPS
            # For cameras, read as fast as possible
            if self._is_video_file and self._frame_delay_ms > 0:
                time.sleep(self._frame_delay_ms / 1000.0)


# Singleton instance — imported by main.py lifespan and fall_analyzer
video_capture = VideoCapture()