#!/usr/bin/env python3
"""
demo.py — Standalone fall detection demo (no FastAPI, no Redis needed).

Run from the fall_detection_service directory:
    python demo.py

Controls:
    Q / ESC  → quit
    R        → reset confidence engine (clear fall state)
    S        → print current signal scores to console
    +/-      → increase / decrease confidence threshold

The window shows:
  - Live webcam feed with MediaPipe skeleton overlay
  - HUD with all signal values and a confidence bar
  - "FALL DETECTED" banner with red overlay when fall is confirmed
"""
import sys
import os
import time

# ── Allow running without installing the package ──────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2

# ── Settings override for local dev (no .env needed) ─────────────────────────
os.environ.setdefault("CAMERA_INDEX",       "0")
os.environ.setdefault("CAMERA_WIDTH",       "640")
os.environ.setdefault("CAMERA_HEIGHT",      "480")
os.environ.setdefault("CAMERA_FPS",         "30")
os.environ.setdefault("DEBUG",              "true")
os.environ.setdefault("REDIS_URL",          "redis://localhost:6379/0")
# Thresholds — adjust here to tune sensitivity during testing
os.environ.setdefault("FALL_CONFIDENCE_THRESHOLD",  "0.65")
os.environ.setdefault("FALL_PERSISTENCE_SECONDS",   "0.4")
os.environ.setdefault("VELOCITY_THRESHOLD",         "150.0")

from app.config import settings
from app.core.video_capture import video_capture
from app.core.fall_analyzer import fall_analyzer
from app.core.confidence_engine import confidence_engine


def print_help():
    print("\n" + "="*55)
    print("  ElderCare — Fall Detection Demo")
    print("="*55)
    print("  Q / ESC  quit")
    print("  R        reset fall state")
    print("  S        print signal scores to console")
    print("  +        raise confidence threshold (+0.05)")
    print("  -        lower confidence threshold (−0.05)")
    print(f"\n  Threshold:   {settings.fall_confidence_threshold}")
    print(f"  Persistence: {settings.fall_persistence_seconds}s")
    print(f"  Velocity:    {settings.velocity_threshold}")
    print("="*55 + "\n")


def main():
    print_help()

    # ── Open camera ───────────────────────────────────────────────────────────
    ok = video_capture.start()
    if not ok:
        print(f"\n❌  Cannot open camera index {settings.camera_index}")
        print("    Try setting CAMERA_INDEX=1 or check your webcam connection.\n")
        sys.exit(1)

    print(f"✓  Camera opened (index={settings.camera_index})")
    print("   Waiting for first frame…\n")

    # Wait up to 3s for first frame
    for _ in range(60):
        if video_capture.get_frame() is not None:
            break
        time.sleep(0.05)
    else:
        print("❌  No frames received from camera. Exiting.")
        video_capture.stop()
        sys.exit(1)

    print("✓  Receiving frames. Detection running.\n")

    # ── Dynamic threshold (adjustable at runtime with +/-) ───────────────────
    threshold = settings.fall_confidence_threshold

    # ── FPS counter ──────────────────────────────────────────────────────────
    fps_counter = 0
    fps_display = 0.0
    fps_timer   = time.time()

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        frame = video_capture.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        # Run full pipeline
        result = fall_analyzer.analyze(frame)

        # FPS
        fps_counter += 1
        if time.time() - fps_timer >= 1.0:
            fps_display = fps_counter / (time.time() - fps_timer)
            fps_counter = 0
            fps_timer = time.time()

        # Draw FPS on frame
        display = result.annotated_frame.copy()
        cv2.putText(display, f"FPS: {fps_display:.1f}",
                    (display.shape[1] - 100, display.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        # Draw current threshold
        cv2.putText(display, f"Threshold: {threshold:.2f}",
                    (10, display.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        # Console log on fall
        if result.confidence.is_fall:
            print(f"🚨 FALL DETECTED  confidence={result.confidence.score:.2f}  "
                  f"posture={result.posture}  persist={result.confidence.persistence_seconds:.1f}s  "
                  f"signals={result.confidence.signals}")

        # Show window
        cv2.imshow("ElderCare — Fall Detection Demo  (Q to quit)", display)

        # Keyboard
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):   # Q or ESC
            break
        elif key in (ord('r'), ord('R')):
            confidence_engine.reset()
            print("↺  Fall state reset")
        elif key in (ord('s'), ord('S')):
            print(f"\n── Signal scores ──────────────────")
            print(f"  Posture:     {result.posture}")
            print(f"  Body angle:  {result.body_angle_deg:.1f}°")
            print(f"  Body ratio:  {result.body_ratio:.3f}")
            print(f"  Velocity:    {result.velocity:.3f}")
            print(f"  Confidence:  {result.confidence.score:.3f}")
            print(f"  Signals:     {result.confidence.signals}")
            print(f"  Visibility:  {result.visibility_mode}")
            print(f"  Persistence: {result.confidence.persistence_seconds:.2f}s")
            print()
        elif key == ord('+'):
            threshold = min(1.0, threshold + 0.05)
            confidence_engine.update_threshold(threshold)
            print(f"▲  Threshold → {threshold:.2f}")
        elif key == ord('-'):
            threshold = max(0.1, threshold - 0.05)
            confidence_engine.update_threshold(threshold)
            print(f"▼  Threshold → {threshold:.2f}")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    print("\nShutting down…")
    video_capture.stop()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()