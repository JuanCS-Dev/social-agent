import pytest
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


@pytest.mark.asyncio
async def test_operator_task_lifecycle(temp_storage):
    task_id = await temp_storage.queue_operator_task(
        event_id="evt_x_1",
        platform="x",
        action_type="reply",
        thread_ref="tw_1",
        content="resposta sugerida",
        options={"source": "test"},
    )
    assert task_id > 0

    pending = await temp_storage.list_operator_tasks(platform="x", status="pending", limit=10)
    assert len(pending) == 1
    assert pending[0]["thread_ref"] == "tw_1"
    assert pending[0]["options"]["source"] == "test"

    updated = await temp_storage.update_operator_task(
        task_id=task_id,
        status="done",
        external_id="tweet_999",
        notes="executado no web profile",
    )
    assert updated is True

    done = await temp_storage.list_operator_tasks(platform="x", status="done", limit=10)
    assert len(done) == 1
    assert done[0]["external_id"] == "tweet_999"

    stats = await temp_storage.get_operator_queue_stats()
    assert stats["pending"] == 0
    assert stats["done"] == 1
