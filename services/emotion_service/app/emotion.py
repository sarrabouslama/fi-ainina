"""DeepFace-based emotion analysis helpers."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import cv2

from app.config import EMOTION_CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

# Detect DeepFace availability once at import time so we don't spam the logs
try:
    from deepface import DeepFace  # type: ignore

    _DEEPFACE_AVAILABLE = True
except Exception:
    _DEEPFACE_AVAILABLE = False
    logger.warning(
        "DeepFace not installed; emotion analysis disabled."
        " Install with 'pip install deepface' for full functionality."
    )


@dataclass(frozen=True)
class EmotionAnalysisResult:
    """Normalized emotion detection output."""

    emotion: str
    confidence: float
    severity: Optional[str]


def _normalize_confidence(confidence: float) -> float:
    if confidence > 1.0:
        return confidence / 100.0
    return confidence


def _emotion_severity(emotion: str, confidence: float) -> Optional[str]:
    if emotion in {"angry", "fear"} and confidence > 0.6:
        return "high"
    if emotion in {"sad", "disgust"}:
        return "medium"
    if emotion == "surprise":
        return "low"
    return None


def analyze_emotion(face_region) -> EmotionAnalysisResult:
    """Analyze a cropped face region and return the dominant emotion."""
    global _DEEPFACE_AVAILABLE

    
    if face_region is None or getattr(face_region, "size", 0) == 0:
        return EmotionAnalysisResult(emotion="neutral", confidence=0.0, severity=None)

    # If DeepFace isn't available, return neutral without raising repeatedly.
    if not _DEEPFACE_AVAILABLE:
        # Check periodically if we can import it now (e.g. if installed at runtime)
        try:
            from deepface import DeepFace
            _DEEPFACE_AVAILABLE = True
            logger.info("DeepFace is now available.")
        except ImportError:
            return EmotionAnalysisResult(emotion="neutral (DISABLED)", confidence=0.0, severity=None)

    try:
        rgb_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)
        analysis = DeepFace.analyze(
            img_path=rgb_face,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,
        )
        if isinstance(analysis, list):
            analysis = analysis[0]

        emotion_map = analysis.get("emotion", {}) or {}
        dominant_emotion = str(analysis.get("dominant_emotion", "neutral")).lower()
        confidence = _normalize_confidence(float(emotion_map.get(dominant_emotion, 0.0) or 0.0))
        if confidence < EMOTION_CONFIDENCE_THRESHOLD:
            return EmotionAnalysisResult(emotion="neutral", confidence=0.0, severity=None)

        severity = _emotion_severity(dominant_emotion, confidence)
        if dominant_emotion in {"happy", "neutral"}:
            severity = None
        return EmotionAnalysisResult(emotion=dominant_emotion, confidence=confidence, severity=severity)
    except Exception:
        logger.exception("Emotion analysis failed; falling back to neutral")
        return EmotionAnalysisResult(emotion="neutral", confidence=0.0, severity=None)