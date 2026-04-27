"""Unit tests for confidence_engine.py"""
import pytest
from app.core.confidence_engine import ConfidenceEngine

def test_no_fall_all_zeros():
    """Zero scores → no fall."""
    engine = ConfidenceEngine()
    # TODO: uncomment once implemented
    # result = engine.compute(0, 0, 0, 0, "standing")
    # assert result.is_fall == False
    pass

def test_fall_all_ones():
    """Max scores → fall detected."""
    engine = ConfidenceEngine()
    # TODO: uncomment once implemented
    # result = engine.compute(1, 1, 1, 1, "lying")
    # assert result.score > 0.75
    pass
