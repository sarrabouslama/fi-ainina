"""
body_proportions.py — Vertical Span Ratio (VSR) and posture classification.

This module implements CAMERA-INVARIANT posture detection using two signals:

1. TORSO ANGLE (Primary signal)
   - Angle of torso vector vs vertical
   - ~0° = lying flat, ~90° = standing upright
   - Not affected by arm position, camera distance, or angle

2. VERTICAL SPAN RATIO (Secondary signal)  
   - Fraction of body's full length that's vertical: VERTICAL_SPAN / BODY_HEIGHT
   - ~1.0 = standing, ~0.7 = sitting, ~0.3 = lying
   - Camera-invariant: eliminates distance and angle dependency
   
Decision logic:
  STANDING if: angle >= 60° OR VSR >= 0.85
  LYING if:    angle <= 30° AND VSR <= 0.50
  SITTING otherwise (ambiguous zone)

This replaces the previous fragile bounding-box ratio approach, which was
corrupted by arm position and camera framing.
"""
import numpy as np
from typing import Optional, Tuple
from app.core.vision.pose_estimator import PoseResult, LM
from app.config import settings
from app.core.utils.debug_utils import debug_print


# ── Bounding box helpers ──────────────────────────────────────────────────────

def get_bounding_box(pose: PoseResult) -> Optional[Tuple[float, float, float, float]]:
    """
    (x_min, y_min, x_max, y_max) in normalised coords.
    Uses ALL visible landmarks (for body height estimate).
    Returns None if < 4 visible landmarks.
    """
    if not pose.detected or not pose.landmarks:
        return None
    visible = [lm for lm in pose.landmarks if lm.is_visible]
    if len(visible) < 4:
        return None
    xs = [lm.x for lm in visible]
    ys = [lm.y for lm in visible]
    return min(xs), min(ys), max(xs), max(ys)


def _get_torso_bounding_box(pose: PoseResult) -> Optional[Tuple[float, float, float, float]]:
    """
    Bounding box of TORSO landmarks only (shoulders + hips).
    Much more stable than full-body bbox — arm position doesn't affect it.
    """
    if not pose.detected or not pose.landmarks:
        return None

    torso_indices = [LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER, LM.LEFT_HIP, LM.RIGHT_HIP]
    points = [pose.get(idx) for idx in torso_indices]
    visible = [p for p in points if p is not None]

    # Need at least 2 torso points to form a meaningful box
    if len(visible) < 2:
        return None

    xs = [p.x for p in visible]
    ys = [p.y for p in visible]
    return min(xs), min(ys), max(xs), max(ys)


def get_ratio(pose: PoseResult) -> Optional[float]:
    """
    width / height ratio of the TORSO bounding box.
    Using torso-only landmarks prevents arm position from corrupting the ratio.
    Returns None when not enough landmarks.
    
    Note: Landmarks are in NORMALIZED coordinates (0-1), so ratios can be large!
    """
    bb = _get_torso_bounding_box(pose)
    if bb is None:
        debug_print(f"No torso bounding box found", tag="RATIO_CALC")
        return None
    x_min, y_min, x_max, y_max = bb
    h = y_max - y_min
    w = x_max - x_min
    
    debug_print(
        f"torso bbox: x=[{x_min:.3f}, {x_max:.3f}] w={w:.3f}, y=[{y_min:.3f}, {y_max:.3f}] h={h:.3f}",
        tag="RATIO_CALC"
    )
    
    if h < 0.01:  # near-zero height → lying flat, return large ratio
        debug_print(f"h={h:.3f} < 0.01 (near-zero) -> returning 5.0 (lying)", tag="RATIO_CALC")
        return 5.0
    
    ratio = w / h
    debug_print(f"ratio = w/h = {w:.3f} / {h:.3f} = {ratio:.2f}", tag="RATIO_CALC")
    return ratio


def get_body_height_px(pose: PoseResult) -> float:
    """Estimated body height in pixels (uses full bbox for max extent)."""
    bb = get_bounding_box(pose)
    if bb is None:
        return 0.0
    _, y_min, _, y_max = bb
    return (y_max - y_min) * pose.frame_height


# ── Torso angle ───────────────────────────────────────────────────────────────

def get_torso_angle(pose: PoseResult) -> Optional[float]:
    """
    Angle of the torso vector (hip_mid → shoulder_mid) vs vertical, in degrees.
      ~80-90° → standing upright
      ~30-70° → sitting / leaning
       ~0-25° → lying flat

    This is the PRIMARY posture signal.
    
    Uses lenient visibility (0.1+) to accept hips that are barely visible.
    """
    shoulder = pose.midpoint_lenient(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    hip      = pose.midpoint_lenient(LM.LEFT_HIP,      LM.RIGHT_HIP)
    
    debug_print(
        f"shoulder_mid={shoulder}, hip_mid={hip}",
        tag="TORSO_ANGLE_ATTEMPT"
    )

    if shoulder is None:
        shoulder = pose.get_any(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
        debug_print(f"shoulder_mid was None, using single shoulder: {shoulder}", tag="TORSO_ANGLE_ATTEMPT")
    if hip is None:
        hip = pose.get_any(LM.LEFT_HIP, LM.RIGHT_HIP)
        debug_print(f"hip_mid was None, using single hip: {hip}", tag="TORSO_ANGLE_ATTEMPT")

    if shoulder is None or hip is None:
        debug_print(
            f"FAILED: shoulder={shoulder}, hip={hip} -> returning None",
            tag="TORSO_ANGLE_ATTEMPT"
        )
        return None

    dx = shoulder.x - hip.x
    dy = shoulder.y - hip.y  # negative when shoulder is above hip (y increases downward)

    # arctan2(|dx|, |dy|) gives angle from vertical: 0° = perfectly vertical, 90° = horizontal
    angle = float(np.degrees(np.arctan2(abs(dx), abs(dy))))
    debug_print(
        f"SUCCESS: shoulder=({shoulder.x:.3f}, {shoulder.y:.3f}), hip=({hip.x:.3f}, {hip.y:.3f}), "
        f"dx={dx:.3f}, dy={dy:.3f} -> angle={angle:.1f} deg",
        tag="TORSO_ANGLE_CALC"
    )
    return angle


def get_vertical_span_ratio(pose: PoseResult) -> Optional[float]:
    """
    Vertical Span Ratio (VSR): How much of the body's full length is vertical.
    
    Formula:
      BODY_HEIGHT = sqrt((x_mid_ankle - x_mid_shoulder)² + (y_mid_ankle - y_mid_shoulder)²)
      VERTICAL_SPAN = |y_mid_ankle - y_mid_shoulder|
      VSR = VERTICAL_SPAN / BODY_HEIGHT
    
    This is CAMERA-INVARIANT: eliminates distance and angle dependency.
    
    Interpretation:
      VSR ~ 1.0  → standing upright (full body height is vertical)
      VSR ~ 0.7  → sitting (torso folded, legs may be extended)
      VSR ~ 0.3  → lying (body horizontal)
    
    Thresholds:
      0.85-1.0 = STANDING
      0.50-0.85 = SITTING  
      0.00-0.50 = LYING
    """
    # Get midpoints for full body span
    shoulder = pose.midpoint_lenient(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    ankle = pose.midpoint_lenient(LM.LEFT_ANKLE, LM.RIGHT_ANKLE)
    
    if shoulder is None:
        shoulder = pose.get_any(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    if ankle is None:
        # Try to get any ankle even with low visibility
        left_ankle = pose.get_lenient(LM.LEFT_ANKLE, 0.1)
        right_ankle = pose.get_lenient(LM.RIGHT_ANKLE, 0.1)
        if left_ankle and right_ankle:
            ankle = pose.midpoint_lenient(LM.LEFT_ANKLE, LM.RIGHT_ANKLE, 0.1)
        elif left_ankle:
            ankle = left_ankle
        elif right_ankle:
            ankle = right_ankle
    
    if shoulder is None or ankle is None:
        debug_print(
            f"[VSR_CALC] Cannot calculate VSR: shoulder={shoulder}, ankle={ankle}",
            tag="VSR_CALC"
        )
        return None
    
    # Calculate body height (full diagonal distance)
    dx = ankle.x - shoulder.x
    dy = ankle.y - shoulder.y
    body_height = float(np.sqrt(dx*dx + dy*dy))
    
    if body_height < 0.01:  # body too small or invisible
        debug_print(f"[VSR_CALC] body_height={body_height:.4f} too small", tag="VSR_CALC")
        return None
    
    # Calculate vertical span (only y-component)
    vertical_span = abs(dy)
    
    vsr = vertical_span / body_height
    debug_print(
        f"[VSR_CALC] shoulder_y={shoulder.y:.3f}, ankle_y={ankle.y:.3f}, "
        f"vertical_span={vertical_span:.3f}, body_height={body_height:.3f}, VSR={vsr:.3f}",
        tag="VSR_CALC"
    )
    return vsr



# ── Posture classifier ────────────────────────────────────────────────────────

def classify_posture(pose: PoseResult) -> str:
    """
    Returns 'standing' | 'sitting' | 'lying' | 'unknown'.

    SIMPLE PRINCIPLE: Check if body is vertical or horizontal first.
    
    1. PRIMARY SIGNAL: Vertical Span Ratio (VSR) — is body vertical or horizontal?
       - VSR >= 0.85 → Body is VERTICAL (person is upright or sitting upright)
       - VSR <= 0.50 → Body is HORIZONTAL (person is lying)
       - 0.50 < VSR < 0.85 → AMBIGUOUS (sitting or slouching)
    
    2. SECONDARY SIGNAL: Torso angle (for vertical bodies)
       - If body is vertical and angle >= 60° → STANDING
       - If body is vertical and angle < 60° → SITTING
    """
    vsr = get_vertical_span_ratio(pose)
    angle = get_torso_angle(pose)
    
    vsr_str = f"{vsr:.3f}" if vsr is not None else "None"
    angle_str = f"{angle:.1f}°" if angle is not None else "None"
    debug_print(f"[POSTURE_DEBUG] VSR={vsr_str}, angle={angle_str}", tag="POSTURE_DEBUG")

    # If no data, return unknown
    if vsr is None and angle is None:
        debug_print(f"[POSTURE_DEBUG] No VSR and no angle → UNKNOWN", tag="POSTURE_DEBUG")
        return "unknown"

    # ── PRIMARY SIGNAL: VSR (vertical vs horizontal) ────────────────────────
    
    # Body is HORIZONTAL → LYING
    if vsr is not None and vsr <= 0.50:
        debug_print(f"[POSTURE_DEBUG] VSR={vsr:.3f} <= 0.50 (horizontal body) → LYING", tag="POSTURE_DEBUG")
        return "lying"
    
    # Body is VERTICAL → use angle to distinguish STANDING vs SITTING
    if vsr is not None and vsr >= 0.85:
        debug_print(f"[POSTURE_DEBUG] VSR={vsr:.3f} >= 0.85 (vertical body)", tag="POSTURE_DEBUG")
        
        if angle is None:
            # No angle but body is vertical → likely STANDING
            debug_print(f"[POSTURE_DEBUG]   angle=None but body is vertical → STANDING", tag="POSTURE_DEBUG")
            return "standing"
        
        # Use angle to distinguish
        if angle >= 60.0:
            debug_print(f"[POSTURE_DEBUG]   angle={angle:.1f}° >= 60° (upright) → STANDING", tag="POSTURE_DEBUG")
            return "standing"
        else:
            debug_print(f"[POSTURE_DEBUG]   angle={angle:.1f}° < 60° (folded) → SITTING", tag="POSTURE_DEBUG")
            return "sitting"
    
    # ── AMBIGUOUS ZONE: 0.50 < VSR < 0.85 ────────────────────────────────────
    # Body is partially vertical (sitting with slouch, or lying at an angle)
    
    if vsr is not None:  # 0.50 < VSR < 0.85
        debug_print(f"[POSTURE_DEBUG] VSR={vsr:.3f} in (0.50, 0.85) (ambiguous zone)", tag="POSTURE_DEBUG")
        
        if angle is None:
            # Ambiguous VSR, no angle data → assume SITTING
            debug_print(f"[POSTURE_DEBUG]   angle=None, ambiguous VSR → SITTING", tag="POSTURE_DEBUG")
            return "sitting"
        
        # FUSION: Use both VSR and angle together
        # If BOTH signals suggest horizontal, classify as LYING even in ambiguous zone
        # This catches angled lying positions (e.g., lying on side)
        if vsr <= 0.65 and angle <= 45.0:
            debug_print(
                f"[POSTURE_DEBUG]   FUSION: VSR={vsr:.3f} <= 0.65 AND angle={angle:.1f}° <= 45° → LYING (on ground at angle)",
                tag="POSTURE_DEBUG"
            )
            return "lying"
        
        # Otherwise, use angle to decide
        if angle >= 60.0:
            debug_print(f"[POSTURE_DEBUG]   angle={angle:.1f}° >= 60° → STANDING", tag="POSTURE_DEBUG")
            return "standing"
        else:
            debug_print(f"[POSTURE_DEBUG]   angle={angle:.1f}° < 60° → SITTING", tag="POSTURE_DEBUG")
            return "sitting"
    
    # ── FALLBACK: angle only (VSR is None) ─────────────────────────────────────
    # This happens when ankles are out of frame (e.g., close-up of upper body)
    
    if angle is not None:
        debug_print(f"[POSTURE_DEBUG] VSR=None, using angle only", tag="POSTURE_DEBUG")
        
        if angle >= 60.0:
            debug_print(f"[POSTURE_DEBUG]   angle={angle:.1f}° >= 60° → STANDING", tag="POSTURE_DEBUG")
            return "standing"
        elif angle <= 30.0:
            debug_print(f"[POSTURE_DEBUG]   angle={angle:.1f}° <= 30° → LYING", tag="POSTURE_DEBUG")
            return "lying"
        else:
            debug_print(f"[POSTURE_DEBUG]   angle={angle:.1f}° in (30°, 60°) → SITTING", tag="POSTURE_DEBUG")
            return "sitting"
    
    # No data at all
    debug_print(f"[POSTURE_DEBUG] No VSR and no angle → UNKNOWN", tag="POSTURE_DEBUG")
    return "unknown"