"""
angle_calculator.py — All geometric angle computations from pose landmarks.

Coordinate system reminder:
  MediaPipe normalised coords: x in [0,1] left→right, y in [0,1] top→bottom
  So "up" means smaller y value (shoulder.y < hip.y when standing).
"""
import numpy as np
from typing import Optional, Tuple
from app.core.vision.pose_estimator import PoseResult, Landmark, LM
from app.core.utils.debug_utils import debug_print

def body_angle(pose: PoseResult) -> Optional[float]:
    """
    Angle of the torso vs vertical (degrees), range 0–90.
      ~80-90° → standing upright
      ~30-65° → sitting / leaning
       ~0-25° → lying flat

    Vector: hip_mid → shoulder_mid, angle against the Y-axis (vertical).

    FIX: Uses abs(dx) but NOT abs(dy) so the angle is measured correctly
    as deviation from vertical regardless of camera tilt. The result is
    clamped to [0, 90] so it maps cleanly to confidence scores.
    """
    shoulder = pose.midpoint(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    hip      = pose.midpoint(LM.LEFT_HIP,      LM.RIGHT_HIP)

    if shoulder is None:
        shoulder = pose.get_any(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    if hip is None:
        hip = pose.get_any(LM.LEFT_HIP, LM.RIGHT_HIP)

    if shoulder is None or hip is None:
        return None

    dx = shoulder.x - hip.x
    # dy is negative when shoulder is above hip (correct upright orientation).
    # We want: 0° when horizontal (|dy| ≈ 0), 90° when vertical (|dx| ≈ 0).
    dy = shoulder.y - hip.y

    # arctan2(|dx|, |dy|): angle from vertical
    # |dy| handles both normal (shoulder above) and inverted (shoulder below)
    angle_raw = float(np.degrees(np.arctan2(abs(dx), abs(dy))))
    angle = float(np.clip(angle_raw, 0.0, 90.0))
    
    debug_print(
        f"shoulder=({shoulder.x:.3f}, {shoulder.y:.3f}), "
        f"hip=({hip.x:.3f}, {hip.y:.3f}), dx={dx:.3f}, dy={dy:.3f}, "
        f"angle_raw={angle_raw:.1f} deg, angle_clipped={angle:.1f} deg",
        tag="ANGLE_CALC"
    )
    
    return angle


def head_angle(pose: PoseResult) -> Optional[float]:
    """
    Angle of the head vector (ear → nose) vs horizontal (degrees).
      ~80-90° → head upright (nose is well above/below ear line)
      ~0-30°  → head tilted horizontal (lying down or fallen)

    Useful secondary signal: a fall causes the head to go horizontal.
    """
    nose = pose.get(LM.NOSE)
    if nose is None:
        return None

    ear: Optional[Landmark] = None
    le, re = pose.get(LM.LEFT_EAR), pose.get(LM.RIGHT_EAR)
    if le and re:
        ear = Landmark(
            x=(le.x + re.x) / 2,
            y=(le.y + re.y) / 2,
            z=(le.z + re.z) / 2,
            visibility=min(le.visibility, re.visibility),
        )
    else:
        ear = pose.get_any(LM.LEFT_EAR, LM.RIGHT_EAR)

    if ear is None:
        # last resort: use shoulder midpoint as neck proxy
        ear = pose.midpoint(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)

    if ear is None:
        return None

    dx = nose.x - ear.x
    dy = nose.y - ear.y
    # arctan2(|dy|, |dx|): 90° when nose is directly above/below ear (upright head)
    #                        0° when nose is level with ear (head lying flat)
    return float(np.degrees(np.arctan2(abs(dy), abs(dx))))