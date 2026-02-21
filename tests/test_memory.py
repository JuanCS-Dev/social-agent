import pytest
import os
from src.memory.storage import Storage

@pytest.fixture
async def temp_storage(tmp_path):
    # Override db_path for tests
    s = Storage()
    s.db_path = str(tmp_path / "test.db")
    await s.init_db()
    yield s

@pytest.mark.asyncio
async def test_idempotency(temp_storage):
    # First time should be true
    is_new = await temp_storage.check_and_set_idempotency("key1", "x")
    assert is_new is True
    
    # Second time should be false
    is_new_again = await temp_storage.check_and_set_idempotency("key1", "x")
    assert is_new_again is False

@pytest.mark.asyncio
async def test_event_lifecycle(temp_storage):
    # Save event
    payload = {"foo": "bar"}
    await temp_storage.save_event("evt_1", "test_type", payload)
    
    # Fetch it
    event = await temp_storage.fetch_next_event()
    assert event is not None
    assert event["id"] == "evt_1"
    assert event["event_type"] == "test_type"
    assert event["payload"] == payload
    
    # Delete it
    await temp_storage.delete_event("evt_1")
    
    # Verify empty
    event2 = await temp_storage.fetch_next_event()
    assert event2 is None

@pytest.mark.asyncio
async def test_dlq(temp_storage):
    payload = {"bad": "data"}
    await temp_storage.save_to_dlq("evt_2", "test_fail", payload, "Timeout Error")
    # DLQ isn't fetched by fetch_next_event
    event = await temp_storage.fetch_next_event()
    assert event is None
