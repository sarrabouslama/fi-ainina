"""
confidence_engine.py — Combines all signals into a single fall confidence score.

FIX: Separated _above_since (persistence GATE) from _lying_since (persistence
BONUS). Previously both shared one timer — resetting the posture bonus would
also wipe the gate timer, preventing is_fall from ever firing.
"""
import time
from dataclasses import dataclass, field
from typing import Optional, Dict
from app.config import settings


@dataclass
class FallConfidence:
    score: float
    is_fall: bool
    posture: str
    signals: Dict[str, float] = field(default_factory=dict)
    persistence_seconds: float = 0.0


class ConfidenceEngine:

    def __init__(self):
        self._above_since: Optional[float] = None   # gate timer
        self._lying_since: Optional[float] = None   # bonus timer (separate!)
        self._weights = settings.weights
        self._threshold = settings.fall_confidence_threshold
        self._persistence = settings.fall_persistence_seconds

    def compute(
        self,
        body_angle_deg: Optional[float],
        body_ratio: Optional[float],
        velocity_score: float,
        head_angle_deg: Optional[float],
        posture: str,
    ) -> FallConfidence:
        w = self._weights
        now = time.time()

        # Signal 1: body angle — 0° (lying) → 1.0, 90° (standing) → 0.0
        angle_score = float(max(0.0, 1.0 - (body_angle_deg / 90.0))) if body_angle_deg is not None else 0.0

        # Signal 2: bounding box ratio — lying (≥1.2) → 1.0, standing (≤0.5) → 0.0
        if body_ratio is not None:
            ratio_score = float(min(1.0, max(0.0,
                (body_ratio - settings.body_ratio_sitting_min) /
                (settings.body_ratio_lying - settings.body_ratio_sitting_min)
            )))
        else:
            ratio_score = 0.0

        # Signal 3: velocity (already 0→1)
        vel_score = float(min(1.0, max(0.0, velocity_score)))

        # Signal 4: head angle — horizontal head → 1.0, upright → 0.0
        head_score = float(max(0.0, 1.0 - (head_angle_deg / 85.0))) if head_angle_deg is not None else 0.0

        # Signal 5: persistence bonus — ramps up while posture is non-standing
        # Uses _lying_since, which is NEVER touched by the gate logic below.
        if posture in ("lying", "sitting"):
            if self._lying_since is None:
                self._lying_since = now
            persistence_score = float(min(1.0, (now - self._lying_since) / 3.0))
        else:
            self._lying_since = None
            persistence_score = 0.0

        score = float(min(1.0, max(0.0,
            w[0] * angle_score +
            w[1] * ratio_score +
            w[2] * vel_score +
            w[3] * head_score +
            w[4] * persistence_score
        )))

        # Persistence gate — score must stay above threshold for N seconds
        # Uses _above_since, which is NEVER touched by the bonus logic above.
        persistence_elapsed = 0.0
        if score >= self._threshold:
            if self._above_since is None:
                self._above_since = now
            persistence_elapsed = now - self._above_since
            is_fall = persistence_elapsed >= self._persistence
        else:
            self._above_since = None
            is_fall = False

        return FallConfidence(
            score=round(score, 4),
            is_fall=is_fall,
            posture=posture,
            signals={
                "angle":       round(angle_score, 3),
                "ratio":       round(ratio_score, 3),
                "velocity":    round(vel_score, 3),
                "head":        round(head_score, 3),
                "persistence": round(persistence_score, 3),
            },
            persistence_seconds=round(persistence_elapsed, 2),
        )

    def reset(self) -> None:
        self._above_since = None
        self._lying_since = None

    def update_weights(self, weights: list) -> None:
        self._weights = weights

    def update_threshold(self, threshold: float) -> None:
        self._threshold = threshold

    def update_persistence(self, seconds: float) -> None:
        self._persistence = seconds


confidence_engine = ConfidenceEngine()