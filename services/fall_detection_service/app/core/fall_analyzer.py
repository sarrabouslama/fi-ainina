"""
fall_analyzer.py — Main per-frame orchestrator.

Called once per frame. Coordinates all sub-modules and returns
a FallAnalysisResult that main.py / routes / demo use directly.
"""
import time
from dataclasses import dataclass
from typing import Optional
import numpy as np

from app.core.pose_estimator import pose_estimator, PoseResult
from app.core.angle_calculator import body_angle, head_angle
from app.core.body_proportions import get_ratio, classify_posture, get_body_height_px
from app.core.velocity_tracker import velocity_tracker
from app.core.confidence_engine import confidence_engine, FallConfidence
from app.core.visibility_checker import get_visibility_mode, can_detect_fall


@dataclass
class FallAnalysisResult:
    timestamp: float
    visibility_mode: str       # full | partial | none
    posture: str               # standing | sitting | lying | unknown
    body_angle_deg: float
    body_ratio: float
    velocity: float
    confidence: FallConfidence
    annotated_frame: Optional[np.ndarray]   # BGR frame with overlays


class FallAnalyzer:
    """
    Stateless orchestrator — all state lives in the sub-module singletons
    (velocity_tracker, confidence_engine).
    """

    def analyze(self, frame: np.ndarray) -> FallAnalysisResult:
        """Process one BGR frame. Returns a complete FallAnalysisResult."""

        # 1. Pose estimation
        pose: PoseResult = pose_estimator.process(frame)

        # 2. Visibility check
        visibility_mode = get_visibility_mode(pose)

        # 3. Extract raw signals (None when landmarks not visible)
        b_angle = body_angle(pose)       # degrees, None if no torso visible
        h_angle = head_angle(pose)       # degrees, None if no head visible
        b_ratio = get_ratio(pose)        # float, None if not enough landmarks
        posture  = classify_posture(pose)

        # 4. Velocity tracking (always update, even in partial mode)
        velocity_tracker.update(pose)
        vel_score = velocity_tracker.get_velocity_score()  # 0.0 → 1.0

        # 5. Confidence score
        if can_detect_fall(visibility_mode):
            confidence = confidence_engine.compute(
                body_angle_deg=b_angle,
                body_ratio=b_ratio,
                velocity_score=vel_score,
                head_angle_deg=h_angle,
                posture=posture,
            )
        else:
            # Partial or no visibility — produce a zero-confidence result
            # so the pipeline never fires false alerts for invisible people
            from app.core.confidence_engine import FallConfidence
            confidence = FallConfidence(
                score=0.0,
                is_fall=False,
                posture=posture,
                signals={},
                persistence_seconds=0.0,
            )

        # 6. Draw annotated frame
        annotated = pose_estimator.annotate(frame, pose)
        annotated = _draw_hud(
            annotated,
            b_angle, b_ratio, vel_score, posture,
            visibility_mode, confidence,
        )

        return FallAnalysisResult(
            timestamp=time.time(),
            visibility_mode=visibility_mode,
            posture=posture,
            body_angle_deg=b_angle or 0.0,
            body_ratio=b_ratio or 0.0,
            velocity=vel_score,
            confidence=confidence,
            annotated_frame=annotated,
        )


def _draw_hud(
    frame: np.ndarray,
    b_angle: Optional[float],
    b_ratio: Optional[float],
    vel_score: float,
    posture: str,
    visibility_mode: str,
    confidence: FallConfidence,
) -> np.ndarray:
    """Draw the HUD overlay on the annotated frame."""
    import cv2
    h, w = frame.shape[:2]

    # ── Left panel: signal values ─────────────────────────────────────────
    panel_lines = [
        f"Posture:  {posture.upper()}",
        f"Angle:    {b_angle:.1f}°"   if b_angle  is not None else "Angle:    --",
        f"Ratio:    {b_ratio:.2f}"    if b_ratio  is not None else "Ratio:    --",
        f"Velocity: {vel_score:.2f}",
        f"Confidence: {confidence.score:.2f}",
        f"Persist:  {confidence.persistence_seconds:.1f}s",
    ]
    y_start = 55
    for i, line in enumerate(panel_lines):
        y = y_start + i * 22
        cv2.putText(frame, line, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 1, cv2.LINE_AA)

    # ── Confidence bar ────────────────────────────────────────────────────
    bar_x, bar_y, bar_w, bar_h = 10, y_start + len(panel_lines) * 22 + 6, 160, 14
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
    fill = int(bar_w * confidence.score)
    bar_color = (0, 255, 0) if confidence.score < 0.5 else \
                (0, 165, 255) if confidence.score < 0.75 else (0, 0, 255)
    if fill > 0:
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + bar_h), bar_color, -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (120, 120, 120), 1)

    # ── Visibility mode badge ─────────────────────────────────────────────
    badge_color = {"full": (0, 180, 0), "partial": (0, 165, 255), "none": (0, 0, 200)}
    bcolor = badge_color.get(visibility_mode, (100, 100, 100))
    badge_text = f"CAM: {visibility_mode.upper()}"
    cv2.rectangle(frame, (w - 160, 5), (w - 5, 30), bcolor, -1)
    cv2.putText(frame, badge_text, (w - 155, 23),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    # ── FALL DETECTED banner ──────────────────────────────────────────────
    if confidence.is_fall:
        # Semi-transparent red overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 200), -1)
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

        # Bold text centred on screen
        text = "FALL DETECTED"
        font = cv2.FONT_HERSHEY_DUPLEX
        scale = 2.0
        thickness = 3
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
        tx = (w - tw) // 2
        ty = (h + th) // 2

        # Drop shadow
        cv2.putText(frame, text, (tx + 3, ty + 3), font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
        # Main text
        cv2.putText(frame, text, (tx, ty), font, scale, (0, 0, 255), thickness, cv2.LINE_AA)

        # Confidence sub-label
        sub = f"Confidence: {confidence.score:.0%}"
        (sw, _), _ = cv2.getTextSize(sub, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(frame, sub, ((w - sw) // 2, ty + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    return frame


# Singleton
fall_analyzer = FallAnalyzer()