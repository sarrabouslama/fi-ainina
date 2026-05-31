"""Motion-based inactivity tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

import cv2
import numpy as np

from app.config import INACTIVITY_THRESHOLD_SECONDS

MOTION_DIFFERENCE_THRESHOLD = 4.0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class InactivityMeasurement:
    """Result of one inactivity update."""

    inactivity_seconds: int
    is_inactive: bool
    transitioned_to_inactive: bool


class InactivityTimer:
    """Track inactivity based on changes between sampled frames."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._previous_frame: np.ndarray | None = None
        self._last_motion_at = _utc_now()
        self._is_inactive = False

    def update(self, frame) -> InactivityMeasurement:
        """Update the timer from a new sampled frame."""
        if frame is None or getattr(frame, "size", 0) == 0:
            with self._lock:
                inactivity_seconds = int((_utc_now() - self._last_motion_at).total_seconds())
                return InactivityMeasurement(
                    inactivity_seconds=inactivity_seconds,
                    is_inactive=inactivity_seconds >= INACTIVITY_THRESHOLD_SECONDS,
                    transitioned_to_inactive=False,
                )

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

        with self._lock:
            transitioned_to_inactive = False
            if self._previous_frame is not None:
                frame_delta = cv2.absdiff(self._previous_frame, gray_frame)
                motion_score = float(np.mean(frame_delta))
                if motion_score >= MOTION_DIFFERENCE_THRESHOLD:
                    self._last_motion_at = _utc_now()
                    self._is_inactive = False
            else:
                self._last_motion_at = _utc_now()
                self._is_inactive = False

            self._previous_frame = gray_frame
            inactivity_seconds = int((_utc_now() - self._last_motion_at).total_seconds())
            is_inactive = inactivity_seconds >= INACTIVITY_THRESHOLD_SECONDS
            if is_inactive and not self._is_inactive:
                transitioned_to_inactive = True
            self._is_inactive = is_inactive

            return InactivityMeasurement(
                inactivity_seconds=inactivity_seconds,
                is_inactive=is_inactive,
                transitioned_to_inactive=transitioned_to_inactive,
            )