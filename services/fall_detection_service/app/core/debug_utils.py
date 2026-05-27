"""
debug_utils.py — Global debug flag and helpers for tracing posture calculation.

Usage:
  from app.core.debug_utils import enable_debug, debug_print
  enable_debug(True)
  debug_print("message")  # only prints if debug is enabled
"""

_DEBUG = False

def enable_debug(flag: bool):
    """Enable or disable all debug output."""
    global _DEBUG
    _DEBUG = flag
    if _DEBUG:
        print("[DEBUG] Debugging ENABLED")
    else:
        print("[DEBUG] Debugging DISABLED")

def is_debug() -> bool:
    """Check if debugging is enabled."""
    return _DEBUG

def debug_print(message: str, tag: str = "DEBUG"):
    """Print a debug message if debugging is enabled."""
    if _DEBUG:
        print(f"[{tag}] {message}")
