"""
Pytest configuration and shared fixtures.

Run tests with: pytest tests/ -v
Run with coverage: pytest tests/ --cov=app --cov-report=html
"""

import pytest
import asyncio
from datetime import datetime


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_alert_data():
    """Sample alert event data for testing."""
    return {
        "event_type": "fall_detected",
        "user_id": "elder_001",
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "high",
        "confidence": 0.92,
        "metadata": {
            "pose_keypoints": [[10, 20], [30, 40]],
            "camera_id": "camera_001"
        }
    }


@pytest.fixture
def sample_recipients():
    """Sample alert recipients for testing."""
    return [
        {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Alice Dupont",
            "email": "alice@example.com",
            "phone": "+33612345678",
            "role": "family"
        },
        {
            "user_id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "Bob Caregiver",
            "email": "bob@example.com",
            "phone": "+33698765432",
            "role": "caregiver"
        }
    ]


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires services)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )
