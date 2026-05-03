"""
angle_calculator.py — All geometric angle computations from pose landmarks.

Coordinate system reminder:
  MediaPipe normalised coords: x in [0,1] left→right, y in [0,1] top→bottom
  So "up" means smaller y value.
"""
import numpy as np
from typing import Optional, Tuple
from app.core.pose_estimator import PoseResult, Landmark, LM


def three_point_angle(a: Tuple[float, float],
                      b: Tuple[float, float],
                      c: Tuple[float, float]) -> float:
    """Angle at point B formed by vectors BA and BC, in degrees [0, 180]."""
    ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=float)
    bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=float)
    n_ba, n_bc = np.linalg.norm(ba), np.linalg.norm(bc)
    if n_ba == 0 or n_bc == 0:
        return 0.0
    cos_a = np.clip(np.dot(ba, bc) / (n_ba * n_bc), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_a)))


def body_angle(pose: PoseResult) -> Optional[float]:
    """
    Angle of the torso vs vertical (degrees).
      ~90° → standing upright
      ~45° → leaning / sitting
       ~0° → lying flat

    Vector: hip_mid → shoulder_mid, angle against the Y-axis.
    Falls back to single-side landmarks if one side invisible.
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
    dy = shoulder.y - hip.y   # negative when shoulder is above hip (y↓)

    # Angle vs pure vertical  (0° = lying, 90° = upright)
    angle = float(np.degrees(np.arctan2(abs(dx), abs(dy))))
    return angle


def head_angle(pose: PoseResult) -> Optional[float]:
    """
    Angle of the head vector (ear → nose) vs horizontal (degrees).
      ~80-90° → head upright
      ~0-30°  → head tilted / fallen

    Useful secondary signal: a fall causes a sudden head tilt.
    """
    nose = pose.get(LM.NOSE)
    if nose is None:
        return None

    ear: Optional[Landmark] = None
    le, re = pose.get(LM.LEFT_EAR), pose.get(LM.RIGHT_EAR)
    if le and re:
        ear = Landmark(x=(le.x+re.x)/2, y=(le.y+re.y)/2,
                       z=(le.z+re.z)/2, visibility=min(le.visibility, re.visibility))
    else:
        ear = pose.get_any(LM.LEFT_EAR, LM.RIGHT_EAR)

    if ear is None:
        # last resort: use shoulder midpoint as neck proxy
        ear = pose.midpoint(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)

    if ear is None:
        return None

    dx = nose.x - ear.x
    dy = nose.y - ear.y
    return float(np.degrees(np.arctan2(abs(dy), abs(dx))))