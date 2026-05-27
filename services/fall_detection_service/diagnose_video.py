#!/usr/bin/env python3
"""
diagnose_video.py — Debug video file and pose detection issues.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import time
from pathlib import Path
from app.core.pose_estimator import pose_estimator
from app.core.body_proportions import classify_posture, get_torso_angle, get_vertical_span_ratio
from app.core.debug_utils import enable_debug

enable_debug(True)

def diagnose_video(video_path: str):
    """Diagnose video file and pose detection."""
    
    print("\n" + "="*80)
    print("VIDEO DIAGNOSTICS")
    print("="*80)
    
    # 1. Check if file exists
    p = Path(video_path)
    if not p.exists():
        print(f"\n❌ File not found: {video_path}")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Absolute path would be: {p.resolve()}")
        return
    
    print(f"\n✓ File exists: {video_path}")
    print(f"  Size: {p.stat().st_size / 1024 / 1024:.1f} MB")
    
    # 2. Try to open with OpenCV
    print("\n" + "-"*80)
    print("Testing OpenCV VideoCapture...")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("❌ OpenCV cannot open video file")
        print("   Try: ffmpeg -i video.mp4 -c:v libx264 -c:a aac video_converted.mp4")
        return
    
    print("✓ OpenCV opened successfully")
    
    # Get video properties
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Resolution: {width}x{height}")
    print(f"  Duration: {frame_count / fps:.1f}s")
    
    # 3. Try to read first frame
    print("\n" + "-"*80)
    print("Testing frame reading...")
    
    ret, frame = cap.read()
    if not ret or frame is None:
        print("❌ Cannot read first frame")
        cap.release()
        return
    
    print(f"✓ First frame read successfully: {frame.shape}")
    
    # 4. Test pose detection
    print("\n" + "-"*80)
    print("Testing MediaPipe pose detection on first frame...")
    
    pose = pose_estimator.process(frame)
    print(f"  Detected: {pose.detected}")
    print(f"  Landmarks: {len(pose.landmarks) if pose.detected else 0}")
    
    if pose.detected:
        posture = classify_posture(pose)
        angle = get_torso_angle(pose)
        vsr = get_vertical_span_ratio(pose)
        print(f"  Posture: {posture}")
        print(f"  Angle: {angle:.1f}°" if angle else "  Angle: N/A")
        print(f"  VSR: {vsr:.2f}" if vsr else "  VSR: N/A")
    else:
        print("  ⚠️  No pose detected in first frame")
        print("      This could be normal (person not in frame)")
        print("      Checking more frames...")
        
        # Sample frames throughout the video
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        detections = 0
        samples = min(10, frame_count)
        
        for i in range(samples):
            frame_idx = (frame_count // samples) * i
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret:
                pose = pose_estimator.process(frame)
                if pose.detected:
                    detections += 1
                    print(f"      Frame {frame_idx}: ✓ Pose detected")
                else:
                    print(f"      Frame {frame_idx}: ✗ No pose")
        
        print(f"\n  Detection rate: {detections}/{samples} frames")
        if detections == 0:
            print("  ⚠️  No poses detected in sampled frames")
            print("      - Check video contains a person")
            print("      - Check person is reasonably visible/centered")
            print("      - Try different camera angle/distance")
    
    # 5. Test video_capture module
    print("\n" + "-"*80)
    print("Testing video_capture module...")
    
    from app.core.video_capture import video_capture
    
    if not video_capture.start(video_file=video_path):
        print(f"❌ video_capture.start() failed")
        if video_capture.error:
            print(f"   Error: {video_capture.error}")
        cap.release()
        return
    
    print("✓ video_capture started")
    
    # Give it time to read first frame
    time.sleep(0.5)
    
    frame = video_capture.get_frame()
    if frame is None:
        print(f"❌ video_capture.get_frame() returned None")
        print(f"   Running: {video_capture.is_running}")
        print(f"   Frame count: {video_capture.frame_count}")
        if video_capture.error:
            print(f"   Error: {video_capture.error}")
    else:
        print(f"✓ video_capture.get_frame() returned frame: {frame.shape}")
        print(f"   Total frames read: {video_capture.frame_count}")
    
    video_capture.stop()
    cap.release()
    
    print("\n" + "="*80)
    print("DIAGNOSTICS COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_video.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    diagnose_video(video_path)
