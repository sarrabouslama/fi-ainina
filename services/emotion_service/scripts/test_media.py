"""Test emotion and redness detection on images, videos, or a webcam."""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2

from app.capture import _largest_face_bbox, _crop_face
from app.emotion import analyze_emotion
from app.redness import analyze_redness
from app.publisher import RedisEventPublisher


def _overlay(frame, lines):
    y = 28
    for line in lines:
        cv2.putText(frame, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
        y += 28


def _analyze_frame(frame):
    bbox = _largest_face_bbox(frame)
    if bbox is None:
        return None, analyze_emotion(None), analyze_redness(None)
    face = _crop_face(frame, bbox)
    return bbox, analyze_emotion(face), analyze_redness(face)


def run_image(path: Path) -> int:
    frame = cv2.imread(str(path))
    if frame is None:
        print(f"Unable to read image: {path}", file=sys.stderr)
        return 2

    bbox, emotion_result, redness_result = _analyze_frame(frame)
    if bbox is not None:
        x, y, w, h = bbox
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

    _overlay(
        frame,
        [
            f"Emotion: {emotion_result.emotion} ({emotion_result.confidence:.2f})",
            f"Redness: {redness_result.redness_level} ({redness_result.redness_score:.3f})",
            f"Reliable: {redness_result.redness_reliable}",
        ],
    )

    print(
        {
            "emotion": emotion_result.emotion,
            "confidence": emotion_result.confidence,
            "redness_level": redness_result.redness_level,
            "redness_score": redness_result.redness_score,
            "redness_reliable": redness_result.redness_reliable,
        }
    )

    # Publish to Redis for testing
    publisher = RedisEventPublisher()
    
    # Check for distress
    if emotion_result.severity is not None and emotion_result.emotion not in {"happy", "neutral"}:
        print(f"Publishing distress alert to Redis: {emotion_result.emotion}")
        publisher.publish_distress_event(
            severity=emotion_result.severity,
            confidence=emotion_result.confidence,
            emotion=emotion_result.emotion,
            score=emotion_result.confidence,
            redness_score=redness_result.redness_score,
            redness_level=redness_result.redness_level,
            redness_reliable=redness_result.redness_reliable,
        )
    
    # Check for extreme redness
    if redness_result.redness_score > 0.8:
        print(f"Publishing extreme redness alert to Redis: {redness_result.redness_score:.3f}")
        publisher.publish_redness_alert(
            redness_score=redness_result.redness_score,
            level=redness_result.redness_level,
        )

    cv2.imshow("emotion test", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return 0


def run_video(path: Path | None, camera_index: int) -> int:
    capture = cv2.VideoCapture(camera_index if path is None else str(path))
    if not capture.isOpened():
        print("Unable to open video source", file=sys.stderr)
        return 2

    while True:
        success, frame = capture.read()
        if not success:
            break

        bbox, emotion_result, redness_result = _analyze_frame(frame)
        if bbox is not None:
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

        _overlay(
            frame,
            [
                f"Emotion: {emotion_result.emotion} ({emotion_result.confidence:.2f})",
                f"Redness: {redness_result.redness_level} ({redness_result.redness_score:.3f})",
                f"Reliable: {redness_result.redness_reliable}",
                "Press q to quit",
            ],
        )

        cv2.imshow("emotion test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    capture.release()
    cv2.destroyAllWindows()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, help="Path to a test image")
    parser.add_argument("--video", type=Path, help="Path to a test video")
    parser.add_argument("--camera", type=int, default=0, help="Camera index for live webcam testing")
    args = parser.parse_args()

    if args.image:
        return run_image(args.image)
    if args.video:
        return run_video(args.video, args.camera)
    return run_video(None, args.camera)


if __name__ == "__main__":
    raise SystemExit(main())