#!/usr/bin/env python3
"""
inspect_landmarks.py — Deep dive debugging for posture classification.

Run with a video file to inspect all detected landmarks frame-by-frame:
    python inspect_landmarks.py video.mp4

This shows:
    - Which landmarks are detected and their visibility scores
    - The actual coordinates (normalized 0-1)
    - Intermediate calculations (angle, ratio)
    - Why posture was classified the way it was
    
Press:
    SPACE    → Pause/resume
    N        → Go to next frame
    P        → Go to previous frame
    S        → Save detailed report for current frame
    Q / ESC  → Quit
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from app.core.video_capture import video_capture
from app.core.pose_estimator import pose_estimator, LM
from app.core.body_proportions import get_ratio, get_torso_angle, classify_posture, _get_torso_bounding_box
from app.core.angle_calculator import body_angle


# Landmark names for display
LANDMARK_NAMES = {
    LM.NOSE: "Nose",
    LM.LEFT_SHOULDER: "L_Shoulder",
    LM.RIGHT_SHOULDER: "R_Shoulder",
    LM.LEFT_HIP: "L_Hip",
    LM.RIGHT_HIP: "R_Hip",
    LM.LEFT_ELBOW: "L_Elbow",
    LM.RIGHT_ELBOW: "R_Elbow",
    LM.LEFT_WRIST: "L_Wrist",
    LM.RIGHT_WRIST: "R_Wrist",
    LM.LEFT_KNEE: "L_Knee",
    LM.RIGHT_KNEE: "R_Knee",
    LM.LEFT_ANKLE: "L_Ankle",
    LM.RIGHT_ANKLE: "R_Ankle",
    LM.LEFT_EAR: "L_Ear",
    LM.RIGHT_EAR: "R_Ear",
    LM.LEFT_HEEL: "L_Heel",
    LM.RIGHT_HEEL: "R_Heel",
    LM.LEFT_FOOT: "L_Foot",
    LM.RIGHT_FOOT: "R_Foot",
}

# Key torso landmarks for posture detection
KEY_LANDMARKS = [
    LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER,
    LM.LEFT_HIP, LM.RIGHT_HIP,
]


def format_landmark_report(pose) -> str:
    """Generate detailed landmark report."""
    lines = []
    
    lines.append("\n" + "="*80)
    lines.append("  LANDMARK DETECTION REPORT")
    lines.append("="*80)
    
    # Total landmarks
    total_detected = sum(1 for lm in pose.landmarks if lm.visibility > 0.1) if pose.landmarks else 0
    lines.append(f"\nTotal landmarks detected: {total_detected} / {len(pose.landmarks) if pose.landmarks else 0}")
    
    # Key landmarks for posture
    lines.append(f"\nKEY TORSO LANDMARKS (for posture):")
    lines.append(f"{'Landmark':<20} {'Visible':<10} {'Coord (x,y,z)':<25} {'Visibility':<12}")
    lines.append("-" * 67)
    
    for idx in KEY_LANDMARKS:
        lm = pose.get(idx) if pose else None
        name = LANDMARK_NAMES.get(idx, f"Landmark_{idx}")
        if lm:
            vis_str = "YES" if lm.visibility > 0.1 else "NO"
            coord_str = f"({lm.x:.3f}, {lm.y:.3f}, {lm.z:.3f})"
            lines.append(f"{name:<20} {vis_str:<10} {coord_str:<25} {lm.visibility:.2f}")
        else:
            lines.append(f"{name:<20} {'NO':<10} {'(not detected)':<25} {0.0:.2f}")
    
    # All visible landmarks
    lines.append(f"\nALL VISIBLE LANDMARKS (visibility > 0.1):")
    lines.append(f"{'Landmark':<20} {'x':<10} {'y':<10} {'z':<10} {'Visibility':<12}")
    lines.append("-" * 62)
    
    if pose.landmarks:
        for idx, lm in enumerate(pose.landmarks):
            if lm.visibility > 0.1:
                name = LANDMARK_NAMES.get(idx, f"LM_{idx}")
                lines.append(f"{name:<20} {lm.x:<10.3f} {lm.y:<10.3f} {lm.z:<10.3f} {lm.visibility:.2f}")
    
    # Angle calculation details
    lines.append(f"\nANGLE CALCULATION:")
    shoulder = pose.midpoint(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER) if pose else None
    if shoulder is None:
        shoulder = pose.get_any(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER) if pose else None
    
    hip = pose.midpoint(LM.LEFT_HIP, LM.RIGHT_HIP) if pose else None
    if hip is None:
        hip = pose.get_any(LM.LEFT_HIP, LM.RIGHT_HIP) if pose else None
    
    if shoulder:
        lines.append(f"  Shoulder midpoint: ({shoulder.x:.3f}, {shoulder.y:.3f}, {shoulder.z:.3f})")
    else:
        lines.append(f"  Shoulder midpoint: NONE (not detected)")
    
    if hip:
        lines.append(f"  Hip midpoint:      ({hip.x:.3f}, {hip.y:.3f}, {hip.z:.3f})")
    else:
        lines.append(f"  Hip midpoint:      NONE (not detected)")
    
    if shoulder and hip:
        dx = shoulder.x - hip.x
        dy = shoulder.y - hip.y
        angle_raw = float(np.degrees(np.arctan2(abs(dx), abs(dy))))
        angle_clipped = float(np.clip(angle_raw, 0.0, 90.0))
        lines.append(f"  dx = {dx:.3f}, dy = {dy:.3f}")
        lines.append(f"  Raw angle:  {angle_raw:.1f}°")
        lines.append(f"  Clipped angle: {angle_clipped:.1f}°")
        
        decision_text = f"  Decision: {angle_clipped:.1f}° → "
        if angle_clipped >= 65:
            decision_text += "STANDING (≥65°)"
        elif angle_clipped <= 25:
            decision_text += "LYING (≤25°)"
        else:
            decision_text += f"AMBIGUOUS ({angle_clipped:.1f}°, check ratio)"
        lines.append(decision_text)
    else:
        lines.append(f"  Cannot calculate angle (missing shoulder or hip)")
        angle_calc = "NONE"
    
    # Ratio calculation details
    lines.append(f"\nRATIO CALCULATION (width/height of torso bbox):")
    bbox = _get_torso_bounding_box(pose) if pose else None
    if bbox:
        x_min, y_min, x_max, y_max = bbox
        w = x_max - x_min
        h = y_max - y_min
        lines.append(f"  Torso bbox: x=[{x_min:.3f}, {x_max:.3f}], y=[{y_min:.3f}, {y_max:.3f}]")
        lines.append(f"  Width: {w:.3f}, Height: {h:.3f}")
        if h < 0.01:
            lines.append(f"  Ratio: SPECIAL (height < 0.01) → 5.0 (lying)")
        else:
            ratio = w / h
            lines.append(f"  Ratio: {w:.3f} / {h:.3f} = {ratio:.2f}")
            
            decision_text = f"  Decision: {ratio:.2f} → "
            if ratio >= 8.0:
                decision_text += "LYING (≥8.0)"
            elif ratio >= 2.0:
                decision_text += "SITTING (2.0-8.0)"
            else:
                decision_text += "STANDING (<2.0)"
            lines.append(decision_text)
    else:
        lines.append(f"  No torso bbox found (missing landmarks)")
    
    # Final classification
    lines.append(f"\nFINAL POSTURE CLASSIFICATION:")
    if pose:
        posture = classify_posture(pose)
        lines.append(f"  Result: {posture.upper()}")
    
    lines.append("=" * 80 + "\n")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("\n❌ Usage: python inspect_landmarks.py <video_file>\n")
        sys.exit(1)
    
    video_file = sys.argv[1]
    if not os.path.isfile(video_file):
        print(f"\n❌ Video file not found: {video_file}\n")
        sys.exit(1)
    
    print(f"\nOpening: {video_file}")
    
    # Open video manually for frame-by-frame control
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"\n❌ Cannot open video\n")
        sys.exit(1)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"FPS: {fps:.1f}, Frames: {frame_count}\n")
    
    print("="*80)
    print("  LANDMARK INSPECTOR")
    print("="*80)
    print("  SPACE    → Pause/resume")
    print("  N        → Next frame")
    print("  P        → Previous frame")
    print("  S        → Save frame report")
    print("  Q / ESC  → Quit")
    print("="*80 + "\n")
    
    current_frame = 0
    playing = True
    
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        
        if not ret:
            print("End of video reached")
            break
        
        # Process frame
        pose = pose_estimator.process(frame)
        annotated = pose_estimator.annotate(frame, pose)
        
        # Draw frame number and posture
        display = annotated.copy()
        posture = classify_posture(pose)
        cv2.putText(
            display,
            f"Frame: {current_frame}/{frame_count}  Posture: {posture.upper()}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        cv2.imshow("Landmark Inspector - Press S for report", display)
        
        # Keyboard
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):  # Q or ESC
            break
        elif key == ord(' '):  # Space
            playing = not playing
            print(f"  {'PAUSED' if not playing else 'PLAYING'}")
        elif key in (ord('n'), ord('N')):  # Next
            playing = False
            current_frame = min(current_frame + 1, frame_count - 1)
            print(f"  Frame {current_frame}/{frame_count}")
        elif key in (ord('p'), ord('P')):  # Previous
            playing = False
            current_frame = max(current_frame - 1, 0)
            print(f"  Frame {current_frame}/{frame_count}")
        elif key in (ord('s'), ord('S')):  # Save report
            report = format_landmark_report(pose)
            print(report)
            
            # Save to file with UTF-8 encoding
            report_file = f"landmark_report_frame_{current_frame}.txt"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"✓ Report saved: {report_file}\n")
        
        if playing:
            current_frame = (current_frame + 1) % frame_count
            time.sleep(1.0 / fps if fps > 0 else 0.033)
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n✓ Inspector closed")


if __name__ == "__main__":
    main()
