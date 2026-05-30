"""Configuration loading for the emotion service."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None and value != "" else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None and value != "" else default


def _get_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value != "" else default


INACTIVITY_THRESHOLD_SECONDS: int = _get_int("INACTIVITY_THRESHOLD_SECONDS", 300)
EMOTION_CONFIDENCE_THRESHOLD: float = _get_float("EMOTION_CONFIDENCE_THRESHOLD", 0.6)
USER_ID: str = _get_str("USER_ID", "elder_001")
REDIS_HOST: str = _get_str("REDIS_HOST", "redis")
REDIS_PORT: int = _get_int("REDIS_PORT", 6379)
FRAME_SAMPLE_RATE: int = max(1, _get_int("FRAME_SAMPLE_RATE", 5))
REDNESS_MILD_THRESHOLD: float = _get_float("REDNESS_MILD_THRESHOLD", 0.18)
REDNESS_HIGH_THRESHOLD: float = _get_float("REDNESS_HIGH_THRESHOLD", 0.28)
SATURATION_RELIABLE_THRESHOLD: float = _get_float("SATURATION_RELIABLE_THRESHOLD", 40.0)