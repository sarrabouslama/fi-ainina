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
from app.core.vision.pose_estimator import PoseResult, LM
from app.core.features.body_proportions import get_body_height_px
from app.config import settings


class VelocityTracker:
    """
    Keeps a short history of (timestamp, hip_y_normalised, body_height_px)
    and computes the current downward velocity.
    """

    def __init__(self, history_seconds: float = 0.5):
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
        Returns vertical velocity in body-heights per second (normalised).
        Positive = moving downward (increasing y in MediaPipe coords).
        Returns 0.0 when not enough history.

        Fix: use frame_height from pose to convert normalised Δy to pixels,
        then divide by body height in pixels → scale-independent ratio/s.
        We approximate frame_height = body_height / typical_body_fraction.
        Since body_height IS in pixels already (from get_body_height_px),
        we only need raw Δy (normalised 0-1) × frame_height to get Δy_px.
        We store body_height_px so we use it as a proxy for frame_height scale.
        """
        if len(self._history) < 2:
            return 0.0

        t0, y0, h0 = self._history[0]
        t1, y1, h1 = self._history[-1]

        dt = t1 - t0
        if dt <= 0:
            return 0.0

        # Average body height in pixels over the window
        avg_body_h_px = (h0 + h1) / 2.0
        if avg_body_h_px <= 0:
            return 0.0

        # Δy in normalised coords (positive = downward)
        dy_norm = y1 - y0

        # We need frame height to convert Δy_norm → Δy_px.
        # MediaPipe y is normalised to [0,1] over frame height, so:
        #   Δy_px = dy_norm * frame_height_px
        # We don't store frame_height directly, but body_height_px is a
        # fraction of it. Use a fixed assumed fraction (body ~70% of frame).
        # This gives a consistent scale regardless of camera distance.
        assumed_body_fraction = 0.70
        estimated_frame_h = avg_body_h_px / assumed_body_fraction

        dy_px = dy_norm * estimated_frame_h          # pixels moved downward
        velocity_px_per_s = dy_px / dt               # px / s

        # Normalise by body height so result is scale-independent
        normalised = velocity_px_per_s / avg_body_h_px  # body-heights / s

        # Convert to "px/s equivalent" that settings.velocity_threshold expects.
        # velocity_threshold default is 200.0 (px/s at reference distance).
        # Re-scale: multiply by a reference body height (150px typical standing).
        REFERENCE_BODY_PX = 150.0
        return float(normalised * REFERENCE_BODY_PX)

    def get_velocity_score(self) -> float:
        """
        Returns a 0.0→1.0 score.
        0.0 = no downward movement
        1.0 = velocity at or above threshold (fast fall signature)
        """
        v = self.get_velocity()
        if v <= 0:
            return 0.0
        return float(min(1.0, v / settings.velocity_threshold))

    def reset(self) -> None:
        self._history.clear()


# Singleton — reused across frames
velocity_tracker = VelocityTracker()