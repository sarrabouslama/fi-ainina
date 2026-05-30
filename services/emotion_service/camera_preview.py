"""Standalone webcam preview for testing emotion detection in a browser."""

from __future__ import annotations

import logging
import threading
import time
import webbrowser
from typing import Optional, Tuple

import cv2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

from app.emotion import analyze_emotion
from app.redness import analyze_redness

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("camera-preview")

app = FastAPI(title="Emotion Camera Preview")

_FRAME_LOCK = threading.Lock()
_LATEST_FRAME: Optional[bytes] = None


def _largest_face_bbox(frame) -> Optional[Tuple[int, int, int, int]]:
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )
    if len(faces) == 0:
        return None
    return max(faces, key=lambda box: box[2] * box[3])


def _crop_face(frame, bbox: Tuple[int, int, int, int]):
    x, y, width, height = bbox
    return frame[y : y + height, x : x + width]


def _overlay_text(frame, lines: list[str]) -> None:
    y = 30
    for line in lines:
        cv2.putText(
            frame,
            line,
            (15, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        y += 28


def _camera_worker() -> None:
    global _LATEST_FRAME

    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        logger.error("Unable to open webcam device 0")
        return

    logger.info("Camera preview started. Open http://127.0.0.1:8050/")

    while True:
        success, frame = capture.read()
        if not success:
            logger.warning("Webcam frame read failed; retrying")
            time.sleep(0.25)
            continue

        bbox = _largest_face_bbox(frame)
        if bbox is not None:
            x, y, width, height = bbox
            cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 255), 2)
            face_region = _crop_face(frame, bbox)
            emotion_result = analyze_emotion(face_region)
            redness_result = analyze_redness(face_region)

            lines = [
                f"Emotion: {emotion_result.emotion} ({emotion_result.confidence:.2f})",
                f"Redness: {redness_result.redness_level} ({redness_result.redness_score:.3f})",
                f"Reliable: {redness_result.redness_reliable}",
            ]
        else:
            lines = ["No face detected", "Move closer to the camera"]

        _overlay_text(frame, lines)

        ok, encoded = cv2.imencode(".jpg", frame)
        if ok:
            with _FRAME_LOCK:
                _LATEST_FRAME = encoded.tobytes()


def _frame_stream():
    while True:
        with _FRAME_LOCK:
            frame = _LATEST_FRAME
        if frame is None:
            time.sleep(0.05)
            continue

        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        time.sleep(0.03)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(
        """
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Emotion Camera Preview</title>
            <style>
              body { margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; }
              .wrap { max-width: 1100px; margin: 0 auto; padding: 24px; }
              h1 { font-size: 24px; margin: 0 0 12px; }
              p { margin: 0 0 16px; color: #94a3b8; }
              img { width: 100%; max-width: 100%; border-radius: 18px; border: 1px solid #334155; background: #020617; }
            </style>
          </head>
          <body>
            <div class="wrap">
              <h1>Emotion Camera Preview</h1>
              <p>Look at the camera, change your expression, and watch the overlay update live.</p>
              <img src="/video" alt="camera preview" />
            </div>
          </body>
        </html>
        """
    )


@app.get("/video")
def video() -> StreamingResponse:
    return StreamingResponse(_frame_stream(), media_type="multipart/x-mixed-replace; boundary=frame")


def main() -> None:
    worker = threading.Thread(target=_camera_worker, daemon=True)
    worker.start()

    webbrowser.open("http://127.0.0.1:8050/")
    uvicorn.run(app, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()