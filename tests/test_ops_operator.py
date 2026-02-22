from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.ingestion.app import app


client = TestClient(app)


def test_ops_operator_list_and_complete(mocker):
    mock_storage = mocker.patch("src.ingestion.routers.ops.storage")
    mock_storage.list_operator_tasks = AsyncMock(
        return_value=[
            {
                "id": 7,
                "platform": "x",
                "action_type": "publish",
                "content": "post",
                "status": "pending",
            }
        ]
    )
    mock_storage.update_operator_task = AsyncMock(return_value=True)

    response = client.get("/ops/operator/tasks?platform=x&status=pending&limit=10")
    assert response.status_code == 200
    assert response.json()["tasks"][0]["id"] == 7

    complete = client.post(
        "/ops/operator/tasks/7/complete",
        json={"status": "done", "external_id": "tw_7", "notes": "ok"},
    )
    assert complete.status_code == 200
    assert complete.json()["task_status"] == "done"


def test_ops_operator_validation(mocker):
    mock_storage = mocker.patch("src.ingestion.routers.ops.storage")
    mock_storage.list_operator_tasks = AsyncMock(return_value=[])
    mock_storage.update_operator_task = AsyncMock(return_value=False)

    invalid_platform = client.get("/ops/operator/tasks?platform=unknown")
    assert invalid_platform.status_code == 400

    invalid_status = client.post(
        "/ops/operator/tasks/99/complete",
        json={"status": "pending"},
    )
    assert invalid_status.status_code == 400
