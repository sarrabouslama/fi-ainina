"""
fall_analysis_pipeline.py — Main per-frame orchestrator.

Called once per frame. Coordinates all sub-modules and returns
a FallAnalysisResult that main.py / routes / demo use directly.
"""
import time
from dataclasses import dataclass
from typing import Optional
import numpy as np

from app.core.vision.pose_estimator import pose_estimator, PoseResult
from app.core.features.angle_calculator import body_angle, head_angle
from app.core.features.body_proportions import get_ratio, classify_posture, get_body_height_px, get_vertical_span_ratio
from app.core.features.velocity_tracker import velocity_tracker
from app.core.analysis.confidence_engine import confidence_engine, FallConfidence
from app.core.features.visibility_checker import get_visibility_mode, can_detect_fall


@dataclass
class FallAnalysisResult:
    timestamp: float
    visibility_mode: str       # full | partial | none
    posture: str               # standing | sitting | lying | unknown
    body_angle_deg: float
    body_ratio: float
    vsr: Optional[float]
    velocity: float
    confidence: FallConfidence
    annotated_frame: Optional[np.ndarray]   # BGR frame with overlays


class FallAnalysisPipeline:
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
        vsr = get_vertical_span_ratio(pose)
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
            from app.core.analysis.confidence_engine import FallConfidence
            confidence = FallConfidence(
                score=0.0,
                is_fall=False,
                posture=posture,
                signals={},
                persistence_seconds=0.0,
            )

        # 6. Annotate skeleton only (HUD overlay is drawn by callers)
        annotated = pose_estimator.annotate(frame, pose)

        return FallAnalysisResult(
            timestamp=time.time(),
            visibility_mode=visibility_mode,
            posture=posture,
            body_angle_deg=b_angle or 0.0,
            body_ratio=b_ratio or 0.0,
            vsr=vsr,
            velocity=vel_score,
            confidence=confidence,
            annotated_frame=annotated,
        )

# Singleton
fall_analyzer = FallAnalysisPipeline()