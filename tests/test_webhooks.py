from fastapi.testclient import TestClient
from src.ingestion.app import app
import hashlib
import hmac
from src.core.config import settings

client = TestClient(app)


def test_reddit_webhook(mocker):
    mocker.patch("src.ingestion.routers.webhooks.storage.save_event")
    response = client.post("/webhooks/reddit/", json={"name": "test_post"})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_meta_webhook_challenge(monkeypatch):
    import src.core.config

    monkeypatch.setattr(src.core.config.settings, "meta_verify_token", "secret_token")

    response = client.get("/webhooks/meta/", params={"hub.mode": "subscribe", "hub.verify_token": "secret_token", "hub.challenge": "12345"})
    assert response.status_code == 200
    assert response.text == "12345"


def test_meta_webhook_invalid_challenge():
    response = client.get("/webhooks/meta/", params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"})
    assert response.status_code == 403


def test_meta_webhook_signature(monkeypatch, mocker):
    mocker.patch("src.ingestion.routers.webhooks.storage.save_event")
    import src.core.config

    monkeypatch.setattr(src.core.config.settings, "environment", "production")

    payload = b'{"entry": [{"id": "123"}]}'
    # Test valid
    valid_sig = "sha256=" + hmac.new(settings.meta_app_secret.encode(), payload, hashlib.sha256).hexdigest()

    response = client.post("/webhooks/meta/", content=payload, headers={"X-Hub-Signature-256": valid_sig})
    assert response.status_code == 200

    # Test invalid
    response_inv = client.post("/webhooks/meta/", content=payload, headers={"X-Hub-Signature-256": "sha256=invalidhash"})
    assert response_inv.status_code == 403

    # Test missing or malformed signature
    response_missing = client.post("/webhooks/meta/", content=payload)
    assert response_missing.status_code == 403

    response_malformed = client.post("/webhooks/meta/", content=payload, headers={"X-Hub-Signature-256": "invalidformat"})
    assert response_malformed.status_code == 403


def test_meta_webhook_challenge_missing_params():
    response = client.get("/webhooks/meta/")
    assert response.status_code == 400


def test_x_webhook_with_token(monkeypatch, mocker):
    import src.core.config

    mocker.patch("src.ingestion.routers.webhooks.storage.save_event")
    monkeypatch.setattr(src.core.config.settings, "x_webhook_token", "tok_x")

    response = client.post(
        "/webhooks/x/",
        json={"tweet_id": "tw_1", "text": "hello"},
        headers={"x-social-agent-token": "tok_x"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    denied = client.post(
        "/webhooks/x/",
        json={"tweet_id": "tw_2", "text": "hello"},
        headers={"x-social-agent-token": "wrong"},
    )
    assert denied.status_code == 403


def test_x_webhook_without_token_when_not_configured(monkeypatch, mocker):
    import src.core.config

    mocker.patch("src.ingestion.routers.webhooks.storage.save_event")
    monkeypatch.setattr(src.core.config.settings, "x_webhook_token", "")

    response = client.post("/webhooks/x/", json={"tweet_id": "tw_3", "text": "ping"})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
