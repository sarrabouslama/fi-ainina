#!/usr/bin/env python3
"""
record_test_video.py — Record test videos from webcam for later analysis.

Usage:
    python record_test_video.py                    # Records to test_video.mp4
    python record_test_video.py ~/sitting_test.mp4  # Records to custom path

Press:
    Q / ESC  → Stop recording
    SPACE    → Pause/resume
    S        → Print recording stats

The script will show:
    - FPS counter
    - Frame count
    - File size (updates in real-time)
"""
import sys
import os
import cv2
import time

os.environ.setdefault("CAMERA_INDEX", "0")
os.environ.setdefault("CAMERA_WIDTH", "640")
os.environ.setdefault("CAMERA_HEIGHT", "480")
os.environ.setdefault("CAMERA_FPS", "30")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import settings


def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else "test_video.mp4"
    
    print("\n" + "="*60)
    print("  Recording Test Video")
    print("="*60)
    print(f"  Output:   {output_file}")
    print(f"  Camera:   index {settings.camera_index}")
    print(f"  Resolution: {settings.camera_width}x{settings.camera_height}")
    print(f"  FPS:      {settings.camera_fps}")
    print("\n  Keys:")
    print("    Q / ESC  → Stop recording")
    print("    SPACE    → Pause/resume")
    print("    S        → Print stats")
    print("="*60 + "\n")

    # Open camera
    cap = cv2.VideoCapture(settings.camera_index)
    if not cap.isOpened():
        print(f"❌  Cannot open camera {settings.camera_index}\n")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  settings.camera_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_height)
    cap.set(cv2.CAP_PROP_FPS,          settings.camera_fps)

    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 codec
    out = cv2.VideoWriter(
        output_file,
        fourcc,
        settings.camera_fps,
        (settings.camera_width, settings.camera_height)
    )

    if not out.isOpened():
        print(f"❌  Cannot create video writer\n")
        cap.release()
        sys.exit(1)

    print(f"✓  Camera opened, video writer ready")
    print(f"✓  Recording to: {output_file}\n")

    frame_count = 0
    fps_counter = 0
    fps_display = 0.0
    fps_timer = time.time()
    paused = False
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("❌  Failed to read frame")
                break

            # Write frame if not paused
            if not paused:
                out.write(frame)
                frame_count += 1

            # Draw status on frame
            status_text = "RECORDING" if not paused else "PAUSED"
            status_color = (0, 255, 0) if not paused else (0, 165, 255)

            display = frame.copy()
            cv2.putText(
                display,
                status_text,
                (display.shape[1] - 180, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                status_color,
                2,
            )

            # FPS counter
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                fps_display = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

            cv2.putText(
                display,
                f"FPS: {fps_display:.1f}  Frames: {frame_count}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (180, 180, 180),
                1,
            )

            # Show frame
            cv2.imshow("Recording Test Video (Q to stop)", display)

            # Keyboard
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):  # Q or ESC
                break
            elif key == ord(' '):  # Space
                paused = not paused
                print(f"  {'PAUSED' if paused else 'RESUMED'}")
            elif key in (ord('s'), ord('S')):
                elapsed = time.time() - start_time
                file_size_mb = os.path.getsize(output_file) / (1024 * 1024) if os.path.exists(output_file) else 0
                print(f"\n  Frames recorded: {frame_count}")
                print(f"  Elapsed time:   {elapsed:.1f}s")
                print(f"  File size:      {file_size_mb:.2f} MB")
                print(f"  Current FPS:    {fps_display:.1f}\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()

        # Print final stats
        elapsed = time.time() - start_time
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024) if os.path.exists(output_file) else 0

        print("\n" + "="*60)
        print("  Recording Complete")
        print("="*60)
        print(f"  Output file:    {output_file}")
        print(f"  Frames recorded: {frame_count}")
        print(f"  Elapsed time:   {elapsed:.1f}s")
        print(f"  File size:      {file_size_mb:.2f} MB")
        print(f"  Average FPS:    {frame_count / elapsed:.1f}" if elapsed > 0 else "  Average FPS:    N/A")
        print("\n  Test the video with:")
        print(f"    python debug_demo.py {output_file}")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()
