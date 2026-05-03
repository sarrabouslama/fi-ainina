"""
visibility_checker.py — Determine how much of the body is visible.

Three modes:
  full    — ≥25 landmarks visible → full detection pipeline runs
  partial — upper body only (head + shoulders) → degraded mode, no alert
  none    — no person detected → no alert
"""
from app.core.pose_estimator import PoseResult, LM
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

# TODO: improve partial mode.

def get_visibility_mode(pose: PoseResult) -> str:
    """Returns 'full' | 'partial' | 'none'."""
    if not pose.detected:
        return "none"

    if pose.visible_count >= settings.camera_quality_min_landmarks:
        return "full"

    # Check if at least upper body is present
    upper_visible = sum(
        1 for idx in _UPPER_BODY if pose.get(idx) is not None
    )
    if upper_visible >= 4:
        return "partial"

    return "none"


def can_detect_fall(visibility_mode: str) -> bool:
    """Only full visibility supports reliable fall detection."""
    return visibility_mode == "full"