"""
pose_estimator.py — MediaPipe Pose wrapper.

Exposes a single PoseEstimator class that:
  - Initialises MediaPipe Pose once at startup
  - Converts OpenCV BGR frames → RGB → MediaPipe
  - Returns a clean PoseResult dataclass (no MediaPipe types leak out)
  - Draws landmarks on the frame and returns annotated JPEG bytes
"""
import mediapipe as mp
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from app.config import settings


# ── MediaPipe landmark indices we use ───────────────────────────────────────
# Full list: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
class LM:
    NOSE           = 0
    LEFT_EYE       = 2
    RIGHT_EYE      = 5
    LEFT_EAR       = 7
    RIGHT_EAR      = 8
    LEFT_SHOULDER  = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW     = 13
    RIGHT_ELBOW    = 14
    LEFT_WRIST     = 15
    RIGHT_WRIST    = 16
    LEFT_HIP       = 23
    RIGHT_HIP      = 24
    LEFT_KNEE      = 25
    RIGHT_KNEE     = 26
    LEFT_ANKLE     = 27
    RIGHT_ANKLE    = 28
    LEFT_HEEL      = 29
    RIGHT_HEEL     = 30
    LEFT_FOOT      = 31
    RIGHT_FOOT     = 32


@dataclass
class Landmark:
    """Single landmark in normalised [0,1] coordinates."""
    x: float
    y: float
    z: float
    visibility: float

    def as_px(self, width: int, height: int) -> Tuple[int, int]:
        """Convert normalised coords to pixel coords."""
        return int(self.x * width), int(self.y * height)

    @property
    def is_visible(self) -> bool:
        return self.visibility >= settings.landmark_visibility_threshold


@dataclass
class PoseResult:
    """Clean result object — no MediaPipe types."""
    landmarks: Optional[List[Landmark]]      # 33 landmarks, or None if no person
    visible_count: int                        # how many have visibility >= threshold
    world_landmarks: Optional[list]          # 3D metric coords (MediaPipe world)
    frame_width: int = 640
    frame_height: int = 480

    @property
    def detected(self) -> bool:
        return self.landmarks is not None and self.visible_count > 0

    def get(self, idx: int) -> Optional[Landmark]:
        """Safe getter — returns None if landmarks missing or landmark invisible."""
        if not self.landmarks or idx >= len(self.landmarks):
            return None
        lm = self.landmarks[idx]
        return lm if lm.is_visible else None

    def get_any(self, *indices: int) -> Optional[Landmark]:
        """Return first visible landmark from the given list of indices."""
        for idx in indices:
            lm = self.get(idx)
            if lm is not None:
                return lm
        return None

    def midpoint(self, idx_a: int, idx_b: int) -> Optional[Landmark]:
        """Return the midpoint between two landmarks if both visible."""
        a = self.get(idx_a)
        b = self.get(idx_b)
        if a is None or b is None:
            return None
        return Landmark(
            x=(a.x + b.x) / 2,
            y=(a.y + b.y) / 2,
            z=(a.z + b.z) / 2,
            visibility=min(a.visibility, b.visibility),
        )


class PoseEstimator:
    """
    Thread-safe MediaPipe Pose wrapper.
    One instance is created at startup and reused for every frame.
    """

    def __init__(self):
        self._mp_pose = mp.solutions.pose
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles

        self._pose = self._mp_pose.Pose(
            static_image_mode=False,                  # video mode — faster tracking
            model_complexity=1,                        # 0=fast, 1=balanced, 2=accurate
            smooth_landmarks=True,                     # temporal smoothing
            enable_segmentation=False,                 # we don't need segmentation mask
            smooth_segmentation=False,
            min_detection_confidence=settings.mediapipe_detection_confidence,
            min_tracking_confidence=settings.mediapipe_tracking_confidence,
        )

    def process(self, frame: np.ndarray) -> PoseResult:
        """
        Run MediaPipe Pose on one BGR frame.
        Returns PoseResult with normalised landmarks.
        """
        h, w = frame.shape[:2]

        # MediaPipe requires RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False          # minor perf optimisation
        result = self._pose.process(rgb)

        if not result.pose_landmarks:
            return PoseResult(
                landmarks=None,
                visible_count=0,
                world_landmarks=None,
                frame_width=w,
                frame_height=h,
            )

        landmarks = [
            Landmark(
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibility=lm.visibility,
            )
            for lm in result.pose_landmarks.landmark
        ]

        visible_count = sum(
            1 for lm in landmarks
            if lm.visibility >= settings.landmark_visibility_threshold
        )

        world_lms = (
            list(result.pose_world_landmarks.landmark)
            if result.pose_world_landmarks else None
        )

        return PoseResult(
            landmarks=landmarks,
            visible_count=visible_count,
            world_landmarks=world_lms,
            frame_width=w,
            frame_height=h,
        )

    def annotate(self, frame: np.ndarray, pose_result: PoseResult) -> np.ndarray:
        """
        Draw landmarks and connections on a copy of the frame.
        Returns the annotated frame (BGR numpy array).
        Adds a visibility count overlay.
        """
        annotated = frame.copy()

        if not pose_result.detected:
            # No person — draw a red "no detection" banner
            cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 30), (0, 0, 180), -1)
            cv2.putText(
                annotated, "No person detected",
                (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
            )
            return annotated

        # Re-create a MediaPipe NormalizedLandmarkList to use the drawing util
        # (we stored raw floats, so we rebuild a lightweight proto-compatible obj)
        mp_pose = self._mp_pose

        # Draw skeleton using MediaPipe draw utils
        # We need the original result — re-process is wasteful, so we draw manually.
        h, w = frame.shape[:2]
        connections = self._mp_pose.POSE_CONNECTIONS

        # Draw connections first (lines, so they appear below dots)
        for conn in connections:
            start_idx, end_idx = conn
            start = pose_result.landmarks[start_idx]
            end   = pose_result.landmarks[end_idx]
            if start.is_visible and end.is_visible:
                sx, sy = start.as_px(w, h)
                ex, ey = end.as_px(w, h)
                cv2.line(annotated, (sx, sy), (ex, ey), (0, 255, 0), 2)

        # Draw landmark dots
        for lm in pose_result.landmarks:
            if lm.is_visible:
                px, py = lm.as_px(w, h)
                cv2.circle(annotated, (px, py), 4, (0, 128, 255), -1)
                cv2.circle(annotated, (px, py), 4, (255, 255, 255), 1)

        # Overlay: visible landmark count
        cv2.putText(
            annotated,
            f"Landmarks: {pose_result.visible_count}/33",
            (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
        )

        return annotated

    def to_jpeg(self, frame: np.ndarray, quality: int = 80) -> bytes:
        """Encode a BGR numpy frame to JPEG bytes."""
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()

    def close(self):
        """Release MediaPipe resources."""
        self._pose.close()


# Singleton instance — imported by fall_analyzer and routes
pose_estimator = PoseEstimator()