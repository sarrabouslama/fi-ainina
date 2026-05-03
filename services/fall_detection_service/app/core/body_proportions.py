"""
body_proportions.py — Bounding-box ratio and posture classification.

Width/height ratio of the visible landmark bounding box:
  standing → tall narrow box   → ratio < 0.5
  sitting  → medium box        → ratio 0.5–0.9
  lying    → wide flat box     → ratio > 1.2
"""
import numpy as np
from typing import Optional, Tuple
from app.core.pose_estimator import PoseResult, LM
from app.config import settings


def get_bounding_box(pose: PoseResult) -> Optional[Tuple[float, float, float, float]]:
    """(x_min, y_min, x_max, y_max) in normalised coords. None if < 4 visible lm."""
    if not pose.detected or not pose.landmarks:
        return None
    visible = [lm for lm in pose.landmarks if lm.is_visible]
    if len(visible) < 4:
        return None
    xs = [lm.x for lm in visible]
    ys = [lm.y for lm in visible]
    return min(xs), min(ys), max(xs), max(ys)


def get_ratio(pose: PoseResult) -> Optional[float]:
    """width / height ratio of bounding box. None when not enough landmarks."""
    bb = get_bounding_box(pose)
    if bb is None:
        return None
    x_min, y_min, x_max, y_max = bb
    h = y_max - y_min
    if h == 0:
        return None
    return (x_max - x_min) / h


def get_body_height_px(pose: PoseResult) -> float:
    """Estimated body height in pixels (for camera quality check)."""
    bb = get_bounding_box(pose)
    if bb is None:
        return 0.0
    _, y_min, _, y_max = bb
    return (y_max - y_min) * pose.frame_height


def classify_posture(pose: PoseResult) -> str:
    """Returns 'standing' | 'sitting' | 'lying' | 'unknown'."""
    ratio = get_ratio(pose)
    if ratio is None:
        return "unknown"
    if ratio < settings.body_ratio_sitting_min:
        return "standing"
    if ratio <= settings.body_ratio_sitting_max:
        return "sitting"
    if ratio >= settings.body_ratio_lying:
        return "lying"
    # transitional zone 0.9–1.2 → lean toward sitting (avoid false positives)
    return "sitting"