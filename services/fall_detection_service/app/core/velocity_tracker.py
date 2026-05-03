"""
velocity_tracker.py — Track vertical velocity of the body centre-of-mass.

Key insight: a real fall produces a fast downward spike (>200 px/s normalised).
Someone deliberately lying down moves slowly (<80 px/s).

Centre-of-mass approximation: midpoint of left_hip & right_hip.
Velocity is normalised by estimated body height so it is camera-distance
independent.
"""
import time
from collections import deque
from typing import Optional, Deque, Tuple
from app.core.pose_estimator import PoseResult, LM
from app.core.body_proportions import get_body_height_px
from app.config import settings


class VelocityTracker:
    """
    Keeps a short history of (timestamp, hip_y_normalised, body_height_px)
    and computes the current downward velocity.
    """

    def __init__(self, history_seconds: float = 0.5):
        # Store (timestamp, y_position) tuples
        # maxlen chosen so we keep ~history_seconds of data at 30 fps
        maxlen = max(5, int(history_seconds * settings.camera_fps))
        self._history: Deque[Tuple[float, float, float]] = deque(maxlen=maxlen)

    def update(self, pose: PoseResult) -> None:
        """Call once per frame. Extracts hip midpoint y and stores it."""
        hip = pose.midpoint(LM.LEFT_HIP, LM.RIGHT_HIP)
        if hip is None:
            hip = pose.get_any(LM.LEFT_HIP, LM.RIGHT_HIP)
        if hip is None:
            return   # no hip visible — skip this frame

        body_h = get_body_height_px(pose)
        self._history.append((time.time(), hip.y, body_h))

    def get_velocity(self) -> float:
        """
        Returns vertical velocity in px/s, normalised by body height.
        Positive = moving downward (increasing y).
        Returns 0.0 when not enough history.
        """
        if len(self._history) < 2:
            return 0.0

        t0, y0, h0 = self._history[0]
        t1, y1, h1 = self._history[-1]

        dt = t1 - t0
        if dt <= 0:
            return 0.0

        # Raw velocity in normalised coords/s
        raw_velocity = (y1 - y0) / dt   # positive = downward

        # Normalise: convert Δy (normalised) to pixels, then divide by height
        avg_height = (h0 + h1) / 2
        if avg_height <= 0:
            return 0.0

        # Δy in pixels = raw_velocity * frame_height / fps … already per-second
        # Normalised velocity: px/s as fraction of body height
        frame_h = self._history[-1][2] / max(self._history[-1][2], 1)
        px_per_second = raw_velocity * self._history[0][2]   # approx

        return float(px_per_second)

    def get_velocity_score(self) -> float:
        """
        Returns a 0.0→1.0 score.
        0.0 = no movement / slow movement
        1.0 = velocity at or above threshold (fast fall)
        """
        v = self.get_velocity()
        if v <= 0:
            return 0.0
        return float(min(1.0, v / settings.velocity_threshold))

    def reset(self) -> None:
        self._history.clear()


# Singleton — reused across frames
velocity_tracker = VelocityTracker()