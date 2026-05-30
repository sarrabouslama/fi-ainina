"""Background webcam capture and analysis loop."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional, Tuple

import cv2

from app.config import FRAME_SAMPLE_RATE
from app.emotion import analyze_emotion
from app.inactivity import InactivityTimer
from app.publisher import RedisEventPublisher
from app.redness import analyze_redness
from app.state import get_state_store

logger = logging.getLogger(__name__)

_capture_thread: Optional[threading.Thread] = None
_capture_lock = threading.Lock()


def _largest_face_bbox(frame) -> Optional[Tuple[int, int, int, int]]:
    """Return the largest detected face bounding box in the frame."""
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        return None
    return max(faces, key=lambda box: box[2] * box[3])


def _crop_face(frame, bbox: Tuple[int, int, int, int]):
    """Crop a face region from the frame using the provided bounding box."""
    x, y, width, height = bbox
    return frame[y : y + height, x : x + width]


def _capture_loop() -> None:
    """Continuously capture frames and update the shared state."""
    logger.info("Emotion capture loop started")
    state_store = get_state_store()
    publisher = RedisEventPublisher()
    inactivity_timer = InactivityTimer()
    frame_index = 0

    while True:
        capture = cv2.VideoCapture(0)
        if not capture.isOpened():
            logger.error("Unable to open webcam device 0; retrying")
            capture.release()
            time.sleep(2)
            continue

        try:
            while True:
                success, frame = capture.read()
                if not success:
                    logger.warning("Webcam frame read failed; reopening capture")
                    break

                frame_index += 1
                if frame_index % FRAME_SAMPLE_RATE != 0:
                    continue

                try:
                    bbox = _largest_face_bbox(frame)
                    face_region = _crop_face(frame, bbox) if bbox is not None else None
                    emotion_result = analyze_emotion(face_region)
                    redness_result = analyze_redness(face_region)
                    inactivity_result = inactivity_timer.update(frame)

                    state_store.update(
                        emotion=emotion_result.emotion,
                        confidence=emotion_result.confidence,
                        redness_score=redness_result.redness_score,
                        redness_level=redness_result.redness_level,
                        redness_reliable=redness_result.redness_reliable,
                        inactivity_seconds=inactivity_result.inactivity_seconds,
                    )

                    if emotion_result.severity is not None and emotion_result.emotion not in {"happy", "neutral"}:
                        publisher.publish_distress_event(
                            severity=emotion_result.severity,
                            confidence=emotion_result.confidence,
                            emotion=emotion_result.emotion,
                            score=emotion_result.confidence,
                            redness_score=redness_result.redness_score,
                            redness_level=redness_result.redness_level,
                            redness_reliable=redness_result.redness_reliable,
                        )

                    if inactivity_result.transitioned_to_inactive:
                        publisher.publish_inactivity_event(duration_seconds=inactivity_result.inactivity_seconds)
                except Exception:
                    logger.exception("Failed to process sampled webcam frame")
        finally:
            capture.release()


def start_capture_thread() -> None:
    """Start the webcam capture worker once per process."""
    global _capture_thread
    with _capture_lock:
        if _capture_thread is not None and _capture_thread.is_alive():
            return

        _capture_thread = threading.Thread(target=_capture_loop, daemon=True, name="emotion-capture")
        _capture_thread.start()
        logger.info("Emotion capture worker thread started")