"""Thread-safe shared state for the emotion service."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from threading import Lock


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class EmotionStateSnapshot:
    """Immutable view of the latest observed user state."""

    emotion: str
    confidence: float
    redness_score: float
    redness_level: str
    redness_reliable: bool
    inactivity_seconds: int
    last_updated: datetime

    def as_dict(self) -> dict:
        """Return a JSON-serializable dictionary representation."""
        payload = asdict(self)
        payload["last_updated"] = self.last_updated.isoformat().replace("+00:00", "Z")
        return payload


class EmotionStateStore:
    """Maintain the latest emotion, redness, and inactivity snapshot."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = EmotionStateSnapshot(
            emotion="neutral",
            confidence=0.0,
            redness_score=0.0,
            redness_level="normal",
            redness_reliable=False,
            inactivity_seconds=0,
            last_updated=_utc_now(),
        )

    def update(
        self,
        *,
        emotion: str,
        confidence: float,
        redness_score: float,
        redness_level: str,
        redness_reliable: bool,
        inactivity_seconds: int,
    ) -> EmotionStateSnapshot:
        """Replace the stored snapshot with the latest observation."""
        with self._lock:
            self._snapshot = EmotionStateSnapshot(
                emotion=emotion,
                confidence=confidence,
                redness_score=redness_score,
                redness_level=redness_level,
                redness_reliable=redness_reliable,
                inactivity_seconds=max(0, inactivity_seconds),
                last_updated=_utc_now(),
            )
            return self._snapshot

    def snapshot(self) -> EmotionStateSnapshot:
        """Return the latest stored snapshot."""
        with self._lock:
            return self._snapshot


STATE = EmotionStateStore()


def get_state_store() -> EmotionStateStore:
    """Return the shared process-local state store."""
    return STATE