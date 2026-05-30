"""
config.py — All settings loaded from environment variables (or .env file).
Access anywhere via: from app.config import settings
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Camera ──────────────────────────────────────────────
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 30

    # ── Redis ───────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_channel_fall: str = "fall_events"

    # ── Person context ──────────────────────────────────────
    # In a real deployment this comes from a JWT/session.
    # For now: one camera = one monitored person.
    default_person_id: str = "00000000-0000-0000-0000-000000000001"

    # ── Fall detection thresholds ───────────────────────────
    fall_confidence_threshold: float = 0.75  # score above which a fall is confirmed
    fall_persistence_seconds: float = 0.5    # score must stay above threshold for this long
    velocity_threshold: float = 200.0        # px/s normalised — above = fast fall signature
    
    # ── Vertical Span Ratio (VSR) thresholds — CAMERA INVARIANT ──
    # VSR = |y_ankle - y_shoulder| / body_height (0-1 range)
    # Much more robust than bounding box ratio
    vsr_standing_min: float = 0.85           # above = standing (nearly full body vertical)
    vsr_sitting_min: float = 0.50            # 0.50-0.85 = sitting
    vsr_lying_max: float = 0.50              # below = lying (body mostly horizontal)
    
    # Torso angle thresholds (in degrees)
    angle_standing_min: float = 60.0         # above = standing
    angle_sitting_min: float = 30.0          # below = lying, above = sitting or standing
    
    # ── FALL DETECTION thresholds (velocity-based) ──
    # A fall is detected by fast transitions from upright to lying
    fall_angular_velocity_threshold: float = 45.0        # degrees/sec — threshold for "fast" collapse
    fall_vsr_velocity_threshold: float = -0.4            # per second — body flattening rate
    fall_intentional_lie_down_time: float = 2.0          # seconds — transitions slower than this are intentional
    fall_alert_timeout: float = 3.0                      # seconds — after this long lying, trigger alert
    fall_confirmation_time: float = 0.5                  # seconds — must be LYING for this long to confirm
    
    # [DEPRECATED] Old bounding box ratio thresholds — kept for fallback only
    # These were designed for normalized coords but are unreliable with arm movement
    body_ratio_sitting_min: float = 2.0      # below this = standing (ratio < 2)
    body_ratio_sitting_max: float = 8.0      # above this = lying (ratio > 8)
    body_ratio_lying: float = 8.0            # >= this = lying
    body_angle_standing_min: float = 70.0    # old threshold, superseded by angle_standing_min

    # ── Confidence weights ───────────────────────────────────
    # Comma-separated: [angle, ratio, velocity, head, persistence]
    # Must sum to 1.0
    confidence_weights: str = "0.25,0.20,0.30,0.10,0.15"

    @property
    def weights(self) -> List[float]:
        return [float(w) for w in self.confidence_weights.split(",")]

    # ── MediaPipe ───────────────────────────────────────────
    mediapipe_detection_confidence: float = 0.5
    mediapipe_tracking_confidence: float = 0.5
    landmark_visibility_threshold: float = 0.5  # below = landmark treated as invisible

    # ── Camera quality ──────────────────────────────────────
    camera_quality_min_landmarks: int = 25   # < this = poor quality warning
    camera_quality_min_height_px: int = 150  # body shorter than this = too far / bad angle

    # ── Video clips ─────────────────────────────────────────
    clips_dir: str = "/app/clips"
    clip_pre_seconds: int = 10   # seconds of buffer kept before the fall
    clip_post_seconds: int = 5   # seconds recorded after fall confirmed

    # ── Service info ─────────────────────────────────────────
    service_name: str = "fall_detection_service"
    service_version: str = "1.0.0"
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        value = str(value).strip().lower()
        if value in {"1", "true", "yes", "on", "debug", "dev", "development"}:
            return True
        if value in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False
        return False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
