"""
fall_detector.py — Fall detection via state machine + velocity thresholds.

A fall is NOT just being "lying" — it's a TRANSITION:
    STANDING/SITTING  →  LYING  (within < 2 seconds, with high angular velocity)

This module layers fall detection on top of the existing posture classifier.
It tracks:
  1. Angular velocity (ω) — how fast torso angle is changing
  2. VSR velocity — how fast body is becoming horizontal
  3. State transitions — upright → lying within a time window
  4. Post-event stillness — fallen people don't reposition

Decision logic is transparent and tunable via config thresholds.
"""
import time
from collections import deque
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

from app.config import settings
from app.core.debug_utils import debug_print


class FallState(Enum):
    """Fall detection state machine."""
    STABLE = "stable"      # Normal posture, no concern
    FALLING = "falling"    # Fast motion detected (might be fall)
    FALLEN = "fallen"      # Lying confirmed after fast motion
    ALERT = "alert"        # Fallen for too long → trigger alert


@dataclass
class FrameSnapshot:
    """Frame data for tracking history and computing velocities."""
    timestamp: float
    posture: str            # "standing" | "sitting" | "lying" | "unknown"
    torso_angle: Optional[float]  # degrees (0-90)
    vsr: Optional[float]    # vertical span ratio (0-1)
    
    # Smoothed values (EMA filtered)
    torso_angle_smooth: Optional[float] = None
    vsr_smooth: Optional[float] = None


class FallDetector:
    """
    Multi-stage fall detection state machine.
    
    Detects falls by tracking:
      1. Angular velocity (primary signal)
      2. VSR velocity (secondary signal)
      3. Posture transitions (context)
      4. Confirmation time (0.5s lying after motion)
      5. Post-event stillness (low angle variance = immobile)
    """
    
    def __init__(self):
        # State machine
        self.state = FallState.STABLE
        self.state_entered_at = time.time()
        
        # Frame history (30 frames @ 30fps ≈ 1 second)
        self.history = deque(maxlen=30)
        
        # Smoothing state (EMA)
        self.angle_smooth = None
        self.vsr_smooth = None
        
        # Fall event tracking
        self.fall_detected_at = None
        self.alert_triggered_at = None
    
    def process_frame(self, posture: str, torso_angle: Optional[float], vsr: Optional[float]) -> Optional[dict]:
        """
        Process a frame and return fall event if detected.
        
        Args:
            posture: "standing" | "sitting" | "lying" | "unknown"
            torso_angle: degrees (0-90) or None
            vsr: vertical span ratio (0-1) or None
        
        Returns:
            Fall event dict if fall detected, else None
        """
        t_now = time.time()
        
        # Apply EMA smoothing
        self.angle_smooth = self._smooth(torso_angle, self.angle_smooth, alpha=0.6)
        self.vsr_smooth = self._smooth(vsr, self.vsr_smooth, alpha=0.6)
        
        # Create snapshot
        snapshot = FrameSnapshot(
            timestamp=t_now,
            posture=posture,
            torso_angle=torso_angle,
            vsr=vsr,
            torso_angle_smooth=self.angle_smooth,
            vsr_smooth=self.vsr_smooth,
        )
        
        self.history.append(snapshot)
        
        # Compute velocities
        angular_velocity = self._compute_angular_velocity()
        vsr_velocity = self._compute_vsr_velocity()
        
        debug_print(
            f"[FALL_DETECT] state={self.state.value}, ω={angular_velocity:.1f}°/s, VSR_vel={vsr_velocity:.3f}/s",
            tag="FALL_DETECT"
        )
        
        # Update state machine
        fall_event = self._update_state_machine(
            t_now,
            posture,
            angular_velocity,
            vsr_velocity,
        )
        
        return fall_event
    
    def _smooth(self, value: Optional[float], prev_smooth: Optional[float], alpha: float) -> Optional[float]:
        """Apply exponential moving average."""
        if value is None:
            return prev_smooth
        if prev_smooth is None:
            return value
        return alpha * prev_smooth + (1 - alpha) * value
    
    def _compute_angular_velocity(self) -> float:
        """Compute torso angular velocity in °/s."""
        if len(self.history) < 2:
            return 0.0
        
        prev = self.history[-2]
        curr = self.history[-1]
        
        if prev.torso_angle_smooth is None or curr.torso_angle_smooth is None:
            return 0.0
        
        dt = max(curr.timestamp - prev.timestamp, 0.001)  # avoid division by zero
        dα = abs(curr.torso_angle_smooth - prev.torso_angle_smooth)
        
        ω = dα / dt  # degrees per second
        return ω
    
    def _compute_vsr_velocity(self) -> float:
        """Compute VSR velocity (how fast body is becoming horizontal)."""
        if len(self.history) < 2:
            return 0.0
        
        prev = self.history[-2]
        curr = self.history[-1]
        
        if prev.vsr_smooth is None or curr.vsr_smooth is None:
            return 0.0
        
        dt = max(curr.timestamp - prev.timestamp, 0.001)
        dvsr = curr.vsr_smooth - prev.vsr_smooth  # negative = body flattening
        
        vsr_velocity = dvsr / dt  # per second
        return vsr_velocity
    
    def _was_upright_recently(self, t_now: float, lookback_seconds: float = 1.5) -> bool:
        """Check if person was STANDING/SITTING in the last N seconds."""
        for snap in self.history:
            if t_now - snap.timestamp > lookback_seconds:
                continue
            if snap.posture in ("standing", "sitting"):
                return True
        return False
    
    def _is_intentional_lie_down(self, t_now: float) -> bool:
        """
        Detect if the person is lying down intentionally (slow transition).
        
        Heuristic:
          - If transition from upright to lying took > 2.0 seconds → intentional
          - If angular velocity was consistently < 20°/s → intentional
        """
        # Find when transition started (first non-lying state)
        first_non_lying_time = None
        for snap in reversed(self.history):
            if snap.posture != "lying":
                first_non_lying_time = snap.timestamp
                break
        
        if first_non_lying_time is None:
            return False  # All recent frames are lying
        
        transition_duration = t_now - first_non_lying_time
        debug_print(
            f"[FALL_DETECT] Transition duration: {transition_duration:.2f}s",
            tag="FALL_DETECT"
        )
        
        if transition_duration > settings.fall_intentional_lie_down_time:
            debug_print(
                f"[FALL_DETECT] Transition too slow ({transition_duration:.2f}s > {settings.fall_intentional_lie_down_time}s) → intentional",
                tag="FALL_DETECT"
            )
            return True
        
        return False
    
    def _post_event_stillness(self, t_now: float, lookback_seconds: float = 1.0) -> float:
        """
        Measure stillness after lying (angle variance).
        Low variance = immobile (fallen), High variance = moving/repositioning.
        
        Returns: Standard deviation of torso angles in the lookback window.
        """
        angles = [
            snap.torso_angle_smooth
            for snap in self.history
            if snap.torso_angle_smooth is not None
            and t_now - snap.timestamp <= lookback_seconds
        ]
        
        if len(angles) < 2:
            return 0.0
        
        # Compute standard deviation
        mean = sum(angles) / len(angles)
        variance = sum((a - mean) ** 2 for a in angles) / len(angles)
        std_dev = variance ** 0.5
        
        return std_dev
    
    def _update_state_machine(
        self,
        t_now: float,
        posture: str,
        angular_velocity: float,
        vsr_velocity: float,
    ) -> Optional[dict]:
        """
        State machine update. Returns fall event if one is triggered.
        
        States:
          STABLE   → FALLING (if fast angular/VSR velocity + was upright)
          FALLING  → FALLEN (if LYING confirmed + not intentional)
          FALLEN   → ALERT (if lying > ALERT_TIMEOUT)
          ANY      → STABLE (if recovery: standing/sitting again)
        """
        # ── HYSTERESIS: Prevent false recovery from posture misclassification ───
        # If in FALLEN/ALERT state and posture momentarily shows SITTING,
        # but the last few frames were LYING, keep the LYING classification.
        # This prevents momentary angle-based misclassification from exiting fallen state.
        
        if self.state in (FallState.FALLEN, FallState.ALERT) and posture == "sitting":
            # Check if we were recently LYING (last 3 frames)
            recent_postures = [snap.posture for snap in list(self.history)[-3:] if snap.posture == "lying"]
            if recent_postures:
                debug_print(
                    f"[FALL_DETECT] HYSTERESIS: Posture is SITTING but recent LYING detected → override to LYING",
                    tag="FALL_DETECT"
                )
                posture = "lying"  # Override the momentary misclassification
        
        # Recovery: if person is standing/sitting again → back to STABLE
        if posture in ("standing", "sitting"):
            if self.state != FallState.STABLE:
                debug_print(
                    f"[FALL_DETECT] Recovery: person is {posture} again → STABLE",
                    tag="FALL_DETECT"
                )
                self.state = FallState.STABLE
                self.state_entered_at = t_now
                self.fall_detected_at = None
                self.alert_triggered_at = None
            return None
        
        # --- State transitions ---
        
        if self.state == FallState.STABLE:
            # Check for fast collapse
            fast_angular = abs(angular_velocity) > settings.fall_angular_velocity_threshold
            fast_vsr = vsr_velocity < settings.fall_vsr_velocity_threshold
            was_upright = self._was_upright_recently(t_now)
            
            if (fast_angular or fast_vsr) and was_upright:
                debug_print(
                    f"[FALL_DETECT] Fast collapse detected! ω={angular_velocity:.1f}°/s, VSR_vel={vsr_velocity:.3f}/s → FALLING",
                    tag="FALL_DETECT"
                )
                self.state = FallState.FALLING
                self.state_entered_at = t_now
        
        elif self.state == FallState.FALLING:
            # Transition to FALLEN if person is lying and not intentional
            if posture == "lying":
                if not self._is_intentional_lie_down(t_now):
                    debug_print(
                        f"[FALL_DETECT] Fast collapse ended in LYING → FALLEN (not intentional)",
                        tag="FALL_DETECT"
                    )
                    self.state = FallState.FALLEN
                    self.state_entered_at = t_now
                    self.fall_detected_at = t_now
                    
                    # Return fall event
                    stillness = self._post_event_stillness(t_now)
                    return {
                        "event": "fall",
                        "timestamp": t_now,
                        "severity": "hard" if angular_velocity > 100 else "soft",
                        "peak_angular_velocity": angular_velocity,
                        "vsr_velocity": vsr_velocity,
                        "post_event_stillness": stillness,
                    }
                else:
                    debug_print(
                        f"[FALL_DETECT] LYING but transition was intentional → back to STABLE",
                        tag="FALL_DETECT"
                    )
                    self.state = FallState.STABLE
                    self.state_entered_at = t_now
            
            # Timeout: if FALLING for > 1 second but never reaches LYING → false alarm
            elif t_now - self.state_entered_at > 1.0:
                debug_print(
                    f"[FALL_DETECT] FALLING timeout without LYING reached → STABLE (false alarm)",
                    tag="FALL_DETECT"
                )
                self.state = FallState.STABLE
                self.state_entered_at = t_now
        
        elif self.state == FallState.FALLEN:
            # Check if person has been lying too long → trigger ALERT
            time_lying = t_now - self.fall_detected_at
            if time_lying > settings.fall_alert_timeout:
                if self.alert_triggered_at is None:
                    debug_print(
                        f"[FALL_DETECT] Person lying for {time_lying:.1f}s > {settings.fall_alert_timeout}s → ALERT!",
                        tag="FALL_DETECT"
                    )
                    self.alert_triggered_at = t_now
                    return {
                        "event": "fall_alert",
                        "timestamp": t_now,
                        "duration_lying_seconds": time_lying,
                    }
        
        return None
