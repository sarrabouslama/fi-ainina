"""Unit tests for angle_calculator.py"""
import pytest
from app.core.angle_calculator import three_point_angle, body_angle

def test_three_point_angle_90_degrees():
    """Right angle should return ~90 degrees."""
    a = (0, 1)
    b = (0, 0)
    c = (1, 0)
    # TODO: uncomment once implemented
    # assert abs(three_point_angle(a, b, c) - 90.0) < 1.0

def test_three_point_angle_180_degrees():
    """Straight line should return ~180 degrees."""
    a = (0, 0)
    b = (1, 0)
    c = (2, 0)
    # TODO: uncomment once implemented
    # assert abs(three_point_angle(a, b, c) - 180.0) < 1.0
