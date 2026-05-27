#!/usr/bin/env python3
"""
debug_demo.py — Fall detection demo with full debugging enabled.

Run from the fall_detection_service directory:

    # Test with webcam:
    python debug_demo.py
    
    # Test with video file:
    python debug_demo.py path/to/video.mp4
    
    # Or test a fall video:
    python debug_demo.py ~/Downloads/fall_test.mov

This is like demo.py but with debugging output enabled.
Watch the console output while the demo runs to see:
  - Shoulder and hip coordinates
  - Angle calculations (dx, dy, arctan2, clipping)
  - Posture decision logic and thresholds applied
"""
import sys
import os
import time

# ── Enable debugging at startup ──────────────────────────────────────────────
os.environ.setdefault("DEBUG", "true")

# ── Allow running without installing the package ──────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import debug utilities FIRST
from app.core.debug_utils import enable_debug

# Enable debugging immediately
enable_debug(True)

import cv2

# ── Settings override for local dev (no .env needed) ─────────────────────────
os.environ.setdefault("CAMERA_INDEX",       "0")
os.environ.setdefault("CAMERA_WIDTH",       "640")
os.environ.setdefault("CAMERA_HEIGHT",      "480")
os.environ.setdefault("CAMERA_FPS",         "30")
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
    print("\n" + "="*60)
    print("  ElderCare — Fall Detection Demo (DEBUG MODE)")
    print("="*60)
    print("  Q / ESC  quit")
    print("  R        reset fall state")
    print("  S        print detailed signal breakdown")
    print("  D        toggle debug logging on/off")
    print("  +        raise confidence threshold (+0.05)")
    print("  -        lower confidence threshold (−0.05)")
    print(f"\n  Threshold:   {settings.fall_confidence_threshold}")
    print(f"  Persistence: {settings.fall_persistence_seconds}s")
    print(f"  Velocity:    {settings.velocity_threshold}")
    print("="*60 + "\n")


def main():
    # Check for video file argument
    video_file = None
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        if not os.path.isfile(video_file):
            print(f"\n❌  Video file not found: {video_file}\n")
            sys.exit(1)
        print(f"✓  Using video file: {video_file}\n")
    else:
        print(f"✓  Using camera index: {settings.camera_index}\n")
    
    print_help()

    # ── Open camera or video ────────────────────────────────────────────────────
    ok = video_capture.start(video_file=video_file)
    if not ok:
        if video_file:
            print(f"\n❌  Cannot open video file: {video_file}\n")
        else:
            print(f"\n❌  Cannot open camera index {settings.camera_index}")
            print("    Try: python debug_demo.py /path/to/video.mp4\n")
        sys.exit(1)

    source_str = f"video file '{video_file}'" if video_file else f"camera {settings.camera_index}"
    print(f"✓  Opened {source_str}")
    print("   Waiting for first frame…\n")

    # Wait up to 3s for first frame
    for _ in range(60):
        if video_capture.get_frame() is not None:
            break
        time.sleep(0.05)
    else:
        print(f"❌  No frames received from {source_str}. Exiting.")
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
        cv2.imshow("ElderCare — Fall Detection Demo (DEBUG) — Q to quit", display)

        # Keyboard
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):   # Q or ESC
            break
        elif key in (ord('r'), ord('R')):
            confidence_engine.reset()
            print("↺  Fall state reset")
        elif key in (ord('d'), ord('D')):
            from app.core.debug_utils import is_debug, enable_debug
            new_state = not is_debug()
            enable_debug(new_state)
        elif key in (ord('s'), ord('S')):
            print(f"\n{'='*75}")
            print(f"  DETAILED SIGNAL DEBUG")
            print(f"{'='*75}")
            print(f"  Visibility:           {result.visibility_mode}")
            print(f"  Landmarks detected:   {bool(result.body_angle_deg or result.body_ratio)}")
            print(f"")
            print(f"  ANGLE (Primary Signal):")
            print(f"    Value:              {result.body_angle_deg:.1f} deg")
            print(f"    Decision thresholds:")
            print(f"      >= 65 deg        -> STANDING (upright)")
            print(f"      25-65 deg        -> AMBIGUOUS (check ratio)")
            print(f"      <= 25 deg        -> LYING (horizontal)")
            print(f"")
            print(f"  RATIO (Tiebreaker Signal):")
            print(f"    Value:              {result.body_ratio:.3f}")
            print(f"    Decision threshold:")
            print(f"      >= 0.8           -> LYING (wide torso)")
            print(f"      < 0.8            -> SITTING (tall torso)")
            print(f"")
            print(f"  FINAL POSTURE:        {result.posture.upper()}")
            print(f"")
            print(f"  Velocity score:       {result.velocity:.3f}")
            print(f"  Confidence score:     {result.confidence.score:.3f}")
            print(f"  Confidence signals:   {result.confidence.signals}")
            print(f"  Persistence:          {result.confidence.persistence_seconds:.2f}s")
            print(f"{'='*75}\n")
        elif key == ord('+'):
            threshold = min(1.0, threshold + 0.05)
        elif key == ord('-'):
            threshold = max(0.0, threshold - 0.05)

    # Cleanup
    cv2.destroyAllWindows()
    video_capture.stop()
    print("\n✓  Demo closed")


if __name__ == "__main__":
    main()
