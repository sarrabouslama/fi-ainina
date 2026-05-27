#!/usr/bin/env python3
"""
demo_fall_detection.py — Example: Using FallDetector with posture classification.

Shows how to:
  1. Continuously get pose from camera/video
  2. Classify posture (STANDING/SITTING/LYING)
  3. Track fall events using FallDetector
  4. Display results in real-time
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
from app.core.video_capture import video_capture
from app.core.pose_estimator import pose_estimator
from app.core.body_proportions import classify_posture, get_torso_angle, get_vertical_span_ratio
from app.core.fall_detector import FallDetector, FallState
from app.core.debug_utils import debug_print, enable_debug


def main():
    # Initialize fall detector
    detector = FallDetector()
    
    # Initialize video source (camera or file)
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        print(f"\nUsing video file: {video_file}")
        video_capture.start(video_file=video_file)
    else:
        print(f"\nUsing camera (index 0)")
        video_capture.start()
    
    # Give the background thread time to read the first frame
    import time
    time.sleep(1.0)
    
    print("\nPress Q to quit\n")
    print("=" * 80)
    print(f"{'Frame':<8} {'Posture':<12} {'Angle':<8} {'VSR':<8} {'Fall State':<12} {'Event':<20}")
    print("=" * 80)
    
    frame_count = 0
    last_print_time = 0
    
    try:
        while True:
            frame = video_capture.get_frame()
            if frame is None:
                # Video ended or reader failed
                break
            
            frame_count += 1
            
            # 1. Get pose
            pose = pose_estimator.process(frame)
            
            if not pose.detected:
                # Print every 30 frames to show progress
                if frame_count % 30 == 0:
                    print(f"{frame_count:<8} {'NO DETECTION':<12}")
                continue
            
            # 2. Classify posture
            posture = classify_posture(pose)
            angle = get_torso_angle(pose)
            vsr = get_vertical_span_ratio(pose)
            
            # 3. Process through fall detector
            fall_event = detector.process_frame(posture, angle, vsr)
            
            # 4. Display results
            angle_str = f"{angle:.1f}°" if angle is not None else "N/A"
            vsr_str = f"{vsr:.2f}" if vsr is not None else "N/A"
            event_str = ""
            
            if fall_event:
                event_type = fall_event.get("event", "unknown")
                if event_type == "fall":
                    severity = fall_event.get("severity", "")
                    event_str = f"[FALL] ({severity})"
                elif event_type == "fall_alert":
                    duration = fall_event.get("duration_lying_seconds", 0)
                    event_str = f"[ALERT] ({duration:.1f}s)"
            
            print(f"{frame_count:<8} {posture:<12} {angle_str:<8} {vsr_str:<8} {detector.state.value:<12} {event_str:<20}")
            
            # Draw on frame and show
            annotated = pose_estimator.annotate(frame, pose)
            
            # Draw posture + state on frame
            color = (0, 255, 0)  # Green
            if detector.state == FallState.FALLING:
                color = (0, 165, 255)  # Orange
            elif detector.state == FallState.FALLEN:
                color = (0, 0, 255)  # Red
            elif detector.state == FallState.ALERT:
                color = (0, 0, 255)  # Red
            
            cv2.putText(
                annotated,
                f"Posture: {posture.upper()}  State: {detector.state.value.upper()}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                color,
                2
            )
            
            if fall_event and fall_event.get("event") == "fall":
                cv2.putText(
                    annotated,
                    "[!] FALL DETECTED",
                    (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    (0, 0, 255),
                    3
                )
            
            cv2.imshow("Fall Detection Demo", annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):  # Q or ESC
                break
    
    finally:
        video_capture.stop()
        cv2.destroyAllWindows()
        print(f"\n[OK] Demo closed (processed {frame_count} frames)")
        if frame_count == 0:
            print("  WARNING: No frames processed - check video file and camera")
            print("  Diagnostic: python diagnose_video.py <video_path>")


if __name__ == "__main__":
    main()
