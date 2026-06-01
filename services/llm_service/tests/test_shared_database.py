from unittest.mock import AsyncMock, MagicMock

import pytest

from app.external_services import get_long_term_facts, save_conversation_turn


@pytest.mark.asyncio
async def test_get_long_term_facts_uses_shared_user_profile(monkeypatch):
    pool = AsyncMock()
    pool.fetchrow.return_value = {
        "full_name": "Test Elder",
        "role": "elderly",
        "consent_given": True,
        "preferences": {"language": "French", "tone": "cheerful"},
    }

    async def fake_get_pool():
        return pool

    monkeypatch.setattr("app.external_services.get_pool", fake_get_pool)

    result = await get_long_term_facts("11111111-1111-1111-1111-111111111111")

    assert "Name: Test Elder" in result
    assert "Role: elderly" in result
    assert "Consent given: True" in result
    assert "language: French" in result
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_long_term_facts_handles_missing_user(monkeypatch):
    pool = AsyncMock()
    pool.fetchrow.return_value = None

    async def fake_get_pool():
        return pool

    monkeypatch.setattr("app.external_services.get_pool", fake_get_pool)

    result = await get_long_term_facts("missing-user")

    assert result == "No long-term user context available."


@pytest.mark.asyncio
async def test_save_conversation_turn_creates_session_when_needed(monkeypatch):
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=[None, 12])
    conn.execute = AsyncMock()

    transaction = MagicMock()
    transaction.__aenter__.return_value = transaction
    transaction.__aexit__.return_value = None
    conn.transaction.return_value = transaction

    acquire = MagicMock()
    acquire.__aenter__.return_value = conn
    acquire.__aexit__.return_value = None

    pool = MagicMock()
    pool.acquire.return_value = acquire

    async def fake_get_pool():
        return pool

    monkeypatch.setattr("app.external_services.get_pool", fake_get_pool)

    await save_conversation_turn("user-1", "hello", "hi")

    assert conn.fetchval.await_count == 2
    assert conn.execute.await_count == 2
