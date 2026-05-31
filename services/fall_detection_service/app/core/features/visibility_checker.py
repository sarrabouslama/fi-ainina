"""
visibility_checker.py — Determine how much of the body is visible.

Three modes:
  full    — enough landmarks for reliable fall detection
  partial — upper body only → degraded mode, no alert
  none    — no person detected → no alert

FIX: When a person is lying down, many leg landmarks get occluded and
visible_count drops below the original threshold of 25. We now also
grant "full" mode when the key TORSO landmarks (shoulders + hips) are
all visible, even if the total count is lower. This prevents the
pipeline from silently skipping fall detection the moment someone falls.
"""
from app.core.vision.pose_estimator import PoseResult, LM
from app.config import settings

# Upper body landmark indices
_UPPER_BODY = {
    LM.NOSE, LM.LEFT_EAR, LM.RIGHT_EAR,
    LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER,
    LM.LEFT_ELBOW, LM.RIGHT_ELBOW,
}

# Lower body landmark indices
_LOWER_BODY = {
    LM.LEFT_HIP, LM.RIGHT_HIP,
    LM.LEFT_KNEE, LM.RIGHT_KNEE,
    LM.LEFT_ANKLE, LM.RIGHT_ANKLE,
}

# The minimum set of landmarks needed to compute angle + ratio + posture.
# All four must be visible to run the full detection pipeline.
_TORSO_LANDMARKS = {
    LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER,
    LM.LEFT_HIP,      LM.RIGHT_HIP,
}


def get_visibility_mode(pose: PoseResult) -> str:
    """Returns 'full' | 'partial' | 'none'."""
    if not pose.detected:
        return "none"

    # Primary path: enough total landmarks
    if pose.visible_count >= settings.camera_quality_min_landmarks:
        return "full"

    # Fallback: even if overall count is low (e.g. person is lying and legs
    # are occluded), grant "full" if all four torso landmarks are visible.
    # This is the critical case for fall detection — we need shoulders + hips.
    torso_visible = sum(
        1 for idx in _TORSO_LANDMARKS if pose.get(idx) is not None
    )
    if torso_visible == len(_TORSO_LANDMARKS):
        return "full"

    # Check if at least upper body is present
    upper_visible = sum(
        1 for idx in _UPPER_BODY if pose.get(idx) is not None
    )
    if upper_visible >= 4:
        return "partial"

    return "none"


def can_detect_fall(visibility_mode: str) -> bool:
    """Full visibility (including torso-only fallback) supports fall detection."""
    return visibility_mode == "full"