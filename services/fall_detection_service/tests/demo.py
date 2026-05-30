"""
demo.py — Standalone fall-detection visualizer.

Usage:
    # Live webcam (default index 0)
    python demo.py

    # Specific camera index
    python demo.py --camera 1

    # Video file
    python demo.py --video /path/to/video.mp4

    # Enable debug prints
    python demo.py --debug

Press Q or ESC to quit.
Press R to manually reset the fall state machine.
Press D to toggle debug output in terminal.
"""

import sys
import os
import argparse
import time
import cv2
import numpy as np

# ── Path setup ────────────────────────────────────────────────────────────────
# Allow running from anywhere: add the project root to sys.path so that
# "from app.xxx import yyy" style imports work without installing a package.
# Adjust REPO_ROOT if your layout differs.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ── Project imports ───────────────────────────────────────────────────────────
from app.config import settings
from app.core.utils.debug_utils import enable_debug

# Pose
from app.core.analysis.fall_detector import FallDetector, FallState
from app.core.analysis.fall_analysis_pipeline import fall_analyzer


# ─────────────────────────────────────────────────────────────────────────────
# Colour palette  (BGR)
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "black":      (0,   0,   0),
    "white":      (255, 255, 255),
    "red":        (0,   0,   200),
    "orange":     (0,   140, 255),
    "yellow":     (0,   220, 220),
    "green":      (0,   200, 80),
    "cyan":       (200, 220, 0),
    "blue":       (220, 100, 0),
    "purple":     (180, 0,   180),
    "grey":       (130, 130, 130),
    "darkgrey":   (50,  50,  50),
    "panel_bg":   (18,  18,  18),
}

STATE_COLORS = {
    FallState.STABLE:   C["green"],
    FallState.FALLING:  C["orange"],
    FallState.FALLEN:   C["red"],
    FallState.ALERT:    C["purple"],
}

POSTURE_COLORS = {
    "standing": C["green"],
    "sitting":  C["yellow"],
    "lying":    C["red"],
    "unknown":  C["grey"],
}

VISIBILITY_COLORS = {
    "full":    C["green"],
    "partial": C["orange"],
    "none":    C["red"],
}


# ─────────────────────────────────────────────────────────────────────────────
# HUD helpers
# ─────────────────────────────────────────────────────────────────────────────

def _text(img, text, pos, scale=0.55, color=C["white"], thickness=1, shadow=True):
    x, y = pos
    if shadow:
        cv2.putText(img, text, (x+1, y+1), cv2.FONT_HERSHEY_SIMPLEX, scale, C["black"], thickness+1, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def _bar(img, x, y, w, h, value, lo=0.0, hi=1.0, color=C["green"], bg=C["darkgrey"], label=""):
    """Horizontal filled bar.  value is clamped to [lo, hi]."""
    frac = max(0.0, min(1.0, (value - lo) / max(hi - lo, 1e-6)))
    cv2.rectangle(img, (x, y), (x + w, y + h), bg, -1)
    fill_w = int(w * frac)
    if fill_w > 0:
        cv2.rectangle(img, (x, y), (x + fill_w, y + h), color, -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), C["grey"], 1)
    if label:
        _text(img, label, (x + w + 6, y + h - 2), scale=0.42, color=C["white"], shadow=False)


def _panel_bg(img, x, y, w, h, alpha=0.55):
    """Semi-transparent dark background rectangle."""
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), C["panel_bg"], -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def _state_badge(img, text, x, y, color):
    """Filled pill badge."""
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 2)
    pad = 8
    cv2.rectangle(img, (x - pad, y - th - pad), (x + tw + pad, y + pad), color, -1)
    cv2.rectangle(img, (x - pad, y - th - pad), (x + tw + pad, y + pad), C["white"], 1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, 0.7, C["white"], 2, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
# Main draw routine
# ─────────────────────────────────────────────────────────────────────────────

def draw_hud(frame, metrics: dict) -> np.ndarray:
    """
    Overlay all HUD panels on *frame* (in-place).

    metrics keys:
        posture, fall_state, visibility_mode,
        body_angle_deg, head_angle_deg, body_ratio, vsr,
        body_height_px, velocity_score,
        confidence_score, persistence_secs, confidence_signals,
        fps, frame_no
    """
    h, w = frame.shape[:2]

    # ── LEFT PANEL: signals ───────────────────────────────────────────────────
    panel_x, panel_y, panel_w, panel_h = 8, 40, 210, 310
    _panel_bg(frame, panel_x, panel_y, panel_w, panel_h)

    lines = [
        ("Body angle",    metrics["body_angle_deg"],  0, 90,   "deg"),
        ("Head angle",    metrics["head_angle_deg"],  0, 90,   "deg"),
        ("Torso ratio",   metrics["body_ratio"],      0, 5,    ""),
        ("VSR",           metrics["vsr"],             0, 1.0,  ""),
        ("Body ht",       metrics["body_height_px"],  0, 480,  "px"),
        ("Velocity",      metrics["velocity_score"],  0, 1.0,  ""),
    ]

    cy = panel_y + 18
    for label, val, lo, hi, unit in lines:
        if val is None:
            display = f"{label}: --"
            bar_val = 0.0
        else:
            display = f"{label}: {val:.1f}{unit}"
            bar_val = val
        _text(frame, display, (panel_x + 6, cy), scale=0.46, color=C["cyan"])
        cy += 16
        _bar(frame, panel_x + 6, cy, panel_w - 20, 7, bar_val, lo, hi, color=C["blue"])
        cy += 14

    # ── LEFT PANEL: confidence sub-signals ───────────────────────────────────
    cy += 4
    _text(frame, "Confidence signals:", (panel_x + 6, cy), scale=0.46, color=C["yellow"])
    cy += 14
    sigs = metrics.get("confidence_signals", {})
    sig_colors = {
        "angle":       C["cyan"],
        "ratio":       C["blue"],
        "velocity":    C["orange"],
        "head":        C["yellow"],
        "persistence": C["purple"],
    }
    for key, sig_color in sig_colors.items():
        val = sigs.get(key, 0.0)
        _text(frame, f"  {key:<12}{val:.2f}", (panel_x + 6, cy), scale=0.42, color=sig_color)
        cy += 13

    # ── RIGHT PANEL: state badges ────────────────────────────────────────────
    panel2_w = 190
    panel2_x = w - panel2_w - 8
    panel2_y = 40
    panel2_h = 130
    _panel_bg(frame, panel2_x, panel2_y, panel2_w, panel2_h)

    # Visibility
    vis = metrics["visibility_mode"]
    vis_col = VISIBILITY_COLORS.get(vis, C["grey"])
    _text(frame, "VISIBILITY", (panel2_x + 8, panel2_y + 18), scale=0.48, color=C["grey"])
    _state_badge(frame, vis.upper(), panel2_x + 8, panel2_y + 46, vis_col)

    # Posture
    posture = metrics["posture"]
    pos_col = POSTURE_COLORS.get(posture, C["grey"])
    _text(frame, "POSTURE", (panel2_x + 8, panel2_y + 72), scale=0.48, color=C["grey"])
    _state_badge(frame, posture.upper(), panel2_x + 8, panel2_y + 100, pos_col)

    # ── FALL STATE banner (top-right) ─────────────────────────────────────────
    fall_state: FallState = metrics["fall_state"]
    fs_col = STATE_COLORS.get(fall_state, C["grey"])
    fs_text = fall_state.value.upper()

    banner_y = panel2_y + panel2_h + 10
    _panel_bg(frame, panel2_x, banner_y, panel2_w, 50)
    _text(frame, "FALL STATE", (panel2_x + 8, banner_y + 16), scale=0.48, color=C["grey"])
    _state_badge(frame, fs_text, panel2_x + 8, banner_y + 42, fs_col)

    # ── CONFIDENCE bar (bottom-centre) ───────────────────────────────────────
    bar_w = min(400, w - 40)
    bar_x = (w - bar_w) // 2
    bar_y_pos = h - 44
    score = metrics["confidence_score"]

    # colour gradient: green → orange → red
    if score < 0.5:
        bc = C["green"]
    elif score < 0.75:
        bc = C["orange"]
    else:
        bc = C["red"]

    _panel_bg(frame, bar_x - 6, bar_y_pos - 20, bar_w + 12, 44)
    _text(frame, f"Fall confidence:  {score:.0%}  ({metrics['persistence_secs']:.1f}s)", 
          (bar_x, bar_y_pos - 4), scale=0.55, color=C["white"])
    _bar(frame, bar_x, bar_y_pos + 2, bar_w, 14, score, 0, 1, color=bc)

    # Threshold marker
    thresh = settings.fall_confidence_threshold
    mx = bar_x + int(bar_w * thresh)
    cv2.line(frame, (mx, bar_y_pos + 1), (mx, bar_y_pos + 17), C["yellow"], 2)
    _text(frame, f"{thresh:.0%}", (mx - 12, bar_y_pos - 5), scale=0.38, color=C["yellow"], shadow=False)

    # ── TOP BAR: FPS / frame counter ────────────────────────────────────────
    cv2.rectangle(frame, (0, 0), (w, 32), C["panel_bg"], -1)
    _text(frame, f"FPS: {metrics['fps']:.1f}   Frame: {metrics['frame_no']}   [R]=Reset  [D]=Debug  [Q/ESC]=Quit",
          (8, 22), scale=0.50, color=C["white"])

    # ── FULL-SCREEN ALERT overlay ─────────────────────────────────────────────
    if fall_state in (FallState.FALLEN, FallState.ALERT):
        overlay = frame.copy()
        alpha = 0.18 if fall_state == FallState.FALLEN else 0.30
        cv2.rectangle(overlay, (0, 0), (w, h), C["red"], -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        label = "⚠  FALL DETECTED" if fall_state == FallState.FALLEN else "🚨  ALERT — PERSON DOWN"
        font = cv2.FONT_HERSHEY_DUPLEX
        scale = 1.6
        thick = 3
        (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
        tx, ty = (w - tw) // 2, h // 2 + th // 2
        cv2.putText(frame, label, (tx + 3, ty + 3), font, scale, C["black"], thick + 2, cv2.LINE_AA)
        cv2.putText(frame, label, (tx, ty), font, scale, C["white"], thick, cv2.LINE_AA)

    return frame


# ─────────────────────────────────────────────────────────────────────────────
# Main demo loop
# ─────────────────────────────────────────────────────────────────────────────

def run_demo(source, debug_mode: bool = False):
    enable_debug(debug_mode)

    # Open capture
    if isinstance(source, str):
        cap = cv2.VideoCapture(source)
        print(f"[DEMO] Opening video file: {source}")
    else:
        cap = cv2.VideoCapture(source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  settings.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_height)
        cap.set(cv2.CAP_PROP_FPS,          settings.camera_fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print(f"[DEMO] Opening camera index: {source}")

    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source}")
        sys.exit(1)

    # Use core analyzer for per-frame processing; keep local detector state
    fall_detector = FallDetector()

    frame_no = 0
    fps_ema = 30.0
    t_prev = time.time()

    cv2.namedWindow("Fall Detection Demo", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Fall Detection Demo", 960, 600)

    print("[DEMO] Running.  Press Q/ESC to quit, R to reset, D to toggle debug.")

    while True:
        ret, frame = cap.read()
        if not ret:
            # Video file ended → loop back
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            fall_detector = FallDetector()
            continue

        frame_no += 1

        # ── FPS ──────────────────────────────────────────────────────────────
        t_now  = time.time()
        dt     = max(t_now - t_prev, 1e-4)
        t_prev = t_now
        fps_ema = 0.9 * fps_ema + 0.1 * (1.0 / dt)

        # Use core analyzer (single source of truth) for per-frame signals
        result = fall_analyzer.analyze(frame)

        # Update detector state machine using analyzer outputs
        fall_detector.process_frame(result.posture, result.body_angle_deg, result.vsr)
        fall_state = fall_detector.state

        annotated = result.annotated_frame if result.annotated_frame is not None else frame

        metrics = {
            "posture":             result.posture,
            "fall_state":          fall_state,
            "visibility_mode":     result.visibility_mode,
            "body_angle_deg":      result.body_angle_deg,
            "head_angle_deg":      None,
            "body_ratio":          result.body_ratio,
            "vsr":                 result.vsr,
            "body_height_px":      0.0,
            "velocity_score":      result.velocity,
            "confidence_score":    result.confidence.score,
            "persistence_secs":    result.confidence.persistence_seconds,
            "confidence_signals":  result.confidence.signals,
            "fps":                 fps_ema,
            "frame_no":            frame_no,
        }

        draw_hud(annotated, metrics)

        cv2.imshow("Fall Detection Demo", annotated)

        # ── Key handling ──────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):   # Q or ESC
            break
        elif key in (ord('r'), ord('R')):
            print("[DEMO] Manual reset")
            fall_detector = FallDetector()
        elif key in (ord('d'), ord('D')):
            from app.core.utils import debug_utils
            new_flag = not debug_utils.is_debug()
            enable_debug(new_flag)

    cap.release()
    cv2.destroyAllWindows()
    print("[DEMO] Done.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fall Detection Demo")
    group  = parser.add_mutually_exclusive_group()
    group.add_argument("--camera", type=int, default=0,
                       help="Camera device index (default: 0)")
    group.add_argument("--video",  type=str,
                       help="Path to a video file")
    parser.add_argument("--debug", action="store_true",
                        help="Enable verbose debug output in terminal")
    args = parser.parse_args()

    source = args.video if args.video else args.camera
    run_demo(source, debug_mode=args.debug)