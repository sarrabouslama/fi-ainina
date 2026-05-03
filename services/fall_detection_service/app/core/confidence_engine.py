"""
confidence_engine.py — Combines all signals into a single fall confidence score.

Signal pipeline (all scores normalised 0.0 → 1.0):
  1. angle_score      — how far the torso is from vertical
  2. ratio_score      — how "flat" the bounding box is
  3. velocity_score   — how fast the body moved downward
  4. head_score       — how much the head tilted
  5. persistence_score — how long the fallen posture has been maintained

A fall is confirmed when the weighted sum exceeds the threshold
AND stays above it for `fall_persistence_seconds`.

Critical design: sitting down slowly and lying down intentionally
will both score LOW on velocity (signal 3), which prevents false positives.
"""
import time
from dataclasses import dataclass, field
from typing import Optional, Dict
from app.config import settings

# TODO: improve fall detection logic. Right now it's not working. 

@dataclass
class FallConfidence:
    score: float                      # 0.0 → 1.0 weighted sum
    is_fall: bool                     # True when score > threshold for long enough
    posture: str                      # standing | sitting | lying | unknown
    signals: Dict[str, float] = field(default_factory=dict)
    persistence_seconds: float = 0.0  # how long above threshold


class ConfidenceEngine:
    """
    Stateful: tracks how long the score has been above the threshold
    to implement persistence (avoids alerting on a single noisy frame).
    """

    def __init__(self):
        self._above_since: Optional[float] = None
        self._weights = settings.weights          # [angle, ratio, velocity, head, persistence]
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
        """
        Compute confidence score for the current frame.
        All raw values are converted to 0→1 scores internally.
        """
        w = self._weights  # [angle, ratio, velocity, head, persistence]

        # ── Signal 1: body angle ─────────────────────────────
        # 0° (lying) → score 1.0 | 90° (standing) → score 0.0
        if body_angle_deg is not None:
            angle_score = float(max(0.0, 1.0 - (body_angle_deg / 90.0)))
        else:
            angle_score = 0.0

        # ── Signal 2: bounding box ratio ─────────────────────
        # lying (ratio > 1.2) → score 1.0 | standing (ratio < 0.5) → score 0.0
        if body_ratio is not None:
            ratio_score = float(min(1.0, max(0.0,
                (body_ratio - settings.body_ratio_sitting_min) /
                (settings.body_ratio_lying - settings.body_ratio_sitting_min)
            )))
        else:
            ratio_score = 0.0

        # ── Signal 3: velocity ───────────────────────────────
        # Already normalised by VelocityTracker
        vel_score = float(min(1.0, max(0.0, velocity_score)))

        # ── Signal 4: head angle ─────────────────────────────
        # upright head ~85° → score 0.0 | tilted head ~10° → score 1.0
        if head_angle_deg is not None:
            head_score = float(max(0.0, 1.0 - (head_angle_deg / 85.0)))
        else:
            head_score = 0.0

        # ── Signal 5: persistence bonus ──────────────────────
        # Rewards staying in a fallen posture vs a brief stumble
        now = time.time()
        if posture == "lying":
            if self._above_since is not None:
                elapsed = now - self._above_since
                # Ramps from 0 → 1 over 3 seconds of continuous lying
                persistence_score = float(min(1.0, elapsed / 3.0))
            else:
                persistence_score = 0.0
        else:
            persistence_score = 0.0
            # Reset persistence timer when person is not lying
            self._above_since = None

        # ── Weighted sum ──────────────────────────────────────
        score = (
            w[0] * angle_score +
            w[1] * ratio_score +
            w[2] * vel_score +
            w[3] * head_score +
            w[4] * persistence_score
        )
        score = float(min(1.0, max(0.0, score)))

        # ── Persistence gate ──────────────────────────────────
        # Score must stay above threshold for N seconds before alert fires.
        # This is the main guard against single-frame false positives.
        persistence_elapsed = 0.0
        if score >= self._threshold:
            if self._above_since is None:
                self._above_since = now
            persistence_elapsed = now - self._above_since
            is_fall = persistence_elapsed >= self._persistence
        else:
            # Score dropped below threshold — reset the timer
            self._above_since = None
            is_fall = False

        signals = {
            "angle":       round(angle_score, 3),
            "ratio":       round(ratio_score, 3),
            "velocity":    round(vel_score, 3),
            "head":        round(head_score, 3),
            "persistence": round(persistence_score, 3),
        }

        return FallConfidence(
            score=round(score, 4),
            is_fall=is_fall,
            posture=posture,
            signals=signals,
            persistence_seconds=round(persistence_elapsed, 2),
        )

    def reset(self) -> None:
        """Call after a fall has been emitted to avoid repeat alerts."""
        self._above_since = None

    def update_weights(self, weights: list) -> None:
        self._weights = weights

    def update_threshold(self, threshold: float) -> None:
        self._threshold = threshold

    def update_persistence(self, seconds: float) -> None:
        self._persistence = seconds


# Singleton
confidence_engine = ConfidenceEngine()