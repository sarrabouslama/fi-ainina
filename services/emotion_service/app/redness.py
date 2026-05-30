"""Redness analysis helpers for a cropped face region."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.config import REDNESS_HIGH_THRESHOLD, REDNESS_MILD_THRESHOLD, SATURATION_RELIABLE_THRESHOLD


@dataclass(frozen=True)
class RednessAnalysisResult:
    """Normalized redness detection output."""

    redness_score: float
    redness_level: str
    redness_reliable: bool


def _central_face_region(face_region: np.ndarray) -> np.ndarray:
    """Focus analysis on the central face area to reduce background false positives."""
    height, width = face_region.shape[:2]
    if height == 0 or width == 0:
        return face_region

    x_margin = max(1, int(width * 0.18))
    y_margin_top = max(1, int(height * 0.12))
    y_margin_bottom = max(1, int(height * 0.10))
    return face_region[
        y_margin_top : max(y_margin_top + 1, height - y_margin_bottom),
        x_margin : max(x_margin + 1, width - x_margin),
    ]


def analyze_redness(face_region) -> RednessAnalysisResult:
    """Measure redness across the provided face region."""
    if face_region is None or getattr(face_region, "size", 0) == 0:
        return RednessAnalysisResult(redness_score=0.0, redness_level="normal", redness_reliable=False)

    central_face = _central_face_region(face_region)
    hsv_face = cv2.cvtColor(central_face, cv2.COLOR_BGR2HSV)
    b_channel, g_channel, r_channel = cv2.split(central_face)

    lower_red_1 = np.array([0, 45, 50])
    upper_red_1 = np.array([12, 255, 255])
    lower_red_2 = np.array([168, 45, 50])
    upper_red_2 = np.array([180, 255, 255])

    red_mask = cv2.inRange(hsv_face, lower_red_1, upper_red_1) | cv2.inRange(hsv_face, lower_red_2, upper_red_2)
    skin_like_mask = cv2.inRange(hsv_face, np.array([0, 35, 35]), np.array([180, 255, 255]))
    red_pixels = int(cv2.countNonZero(red_mask))
    skin_like_pixels = int(cv2.countNonZero(skin_like_mask))
    total_pixels = int(hsv_face.shape[0] * hsv_face.shape[1])

    red_fraction = float(red_pixels / total_pixels) if total_pixels else 0.0
    skin_fraction = float(skin_like_pixels / total_pixels) if total_pixels else 0.0

    mean_red = float(np.mean(r_channel)) if total_pixels else 0.0
    mean_green = float(np.mean(g_channel)) if total_pixels else 0.0
    mean_blue = float(np.mean(b_channel)) if total_pixels else 0.0
    dominance = max(0.0, (mean_red - max(mean_green, mean_blue)) / 255.0)

    redness_score = float((red_fraction * 0.75) + (dominance * 0.25))
    redness_score = min(1.0, redness_score)

    if redness_score >= REDNESS_HIGH_THRESHOLD and dominance >= 0.08 and skin_fraction >= 0.25:
        redness_level = "high"
    elif redness_score >= REDNESS_MILD_THRESHOLD:
        redness_level = "mild"
    else:
        redness_level = "normal"

    mean_saturation = float(np.mean(hsv_face[:, :, 1])) if total_pixels else 0.0
    redness_reliable = mean_saturation >= SATURATION_RELIABLE_THRESHOLD and skin_fraction >= 0.25
    if not redness_reliable:
        redness_level = "normal"
    return RednessAnalysisResult(
        redness_score=redness_score,
        redness_level=redness_level,
        redness_reliable=redness_reliable,
    )