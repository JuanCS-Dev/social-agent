import pytest
from unittest.mock import AsyncMock
from src.connectors.reddit import RedditConnector
from src.connectors.x import XConnector
from src.connectors.meta import MetaConnector
from src.policy.engine import PolicyEngine
from src.core.contracts import Platform, ActionType
import httpx

@pytest.fixture
def policy_engine():
    return PolicyEngine()

@pytest.fixture
def mock_httpx_post(mocker):
    # Mock httpx.AsyncClient.post globally for these tests
    mock_post = AsyncMock()
    mocker.patch("httpx.AsyncClient.post", new=mock_post)
    return mock_post

@pytest.mark.asyncio
async def test_x_publish_success(policy_engine, mock_httpx_post, mocker):
    connector = XConnector(policy_engine)
    
    # Setup mock response
    mock_resp = mocker.MagicMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"data": {"id": "tweet_123"}}
    mock_httpx_post.return_value = mock_resp
    
    res = await connector.publish("Test tweet")
    assert res.ok is True
    assert res.external_id == "tweet_123"
    assert res.platform == Platform.X

@pytest.mark.asyncio
async def test_x_publish_policy_block(policy_engine, mock_httpx_post, monkeypatch):
    import src.core.config
    monkeypatch.setattr(src.core.config.settings, "environment", "production")

    connector = XConnector(policy_engine)
    res = await connector.publish("DELETE all")
    assert res.ok is False
    assert res.error is not None
    assert "High risk" in res.error
    mock_httpx_post.assert_not_called()

@pytest.mark.asyncio
async def test_x_reply_policy_block(policy_engine, mock_httpx_post, monkeypatch):
    import src.core.config
    monkeypatch.setattr(src.core.config.settings, "environment", "production")

    connector = XConnector(policy_engine)
    res = await connector.reply("t1", "DELETE all")
    assert res.ok is False
    mock_httpx_post.assert_not_called()

@pytest.mark.asyncio
async def test_reddit_reply_success(policy_engine, mock_httpx_post, mocker):
    connector = RedditConnector(policy_engine)
    connector._token = "fake_token"  # skip auth for reply test
    
    mock_resp = mocker.MagicMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"json": {"data": {"id": "comment_456"}}}
    mock_httpx_post.return_value = mock_resp
    
    res = await connector.reply("thread_1", "Test reply")
    assert res.ok is True
    assert res.external_id == "comment_456"
    assert res.platform == Platform.REDDIT

@pytest.mark.asyncio
async def test_meta_publish_ig(policy_engine, mock_httpx_post, mocker):
    connector = MetaConnector(policy_engine)
    connector.ig_user_id = "ig_user_1"
    
    # 2 calls for IG: upload then publish
    mock_resp1 = mocker.MagicMock()
    mock_resp1.raise_for_status = lambda: None
    mock_resp1.json.return_value = {"id": "creation_123"}
    
    mock_resp2 = mocker.MagicMock()
    mock_resp2.raise_for_status = lambda: None
    mock_resp2.json.return_value = {"id": "ig_post_456"}
    
    mock_httpx_post.side_effect = [mock_resp1, mock_resp2]
    
    res = await connector.publish("Test IG", options={"target": "instagram"})
    assert res.ok is True
    assert res.external_id == "ig_post_456"
    assert mock_httpx_post.call_count == 2

@pytest.mark.asyncio
async def test_meta_policy_blocks(policy_engine, mock_httpx_post, monkeypatch):
    import src.core.config
    monkeypatch.setattr(src.core.config.settings, "environment", "production")
    
    m = MetaConnector(policy_engine)
    res_pub = await m.publish("DELETE all")
    assert res_pub.ok is False
    res_rep = await m.reply("t1", "DELETE all")
    assert res_rep.ok is False
    mock_httpx_post.assert_not_called()

@pytest.mark.asyncio
async def test_reddit_policy_blocks(policy_engine, mock_httpx_post, monkeypatch):
    import src.core.config
    monkeypatch.setattr(src.core.config.settings, "environment", "production")
    
    r = RedditConnector(policy_engine)
    r._token = "fake_token"
    res_pub = await r.publish("DELETE all", options={"subreddit": "test"})
    assert res_pub.ok is False
    res_rep = await r.reply("t1", "DELETE all")
    assert res_rep.ok is False
    mock_httpx_post.assert_not_called()
