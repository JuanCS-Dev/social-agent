import pytest
from src.connectors.x import XConnector
from src.connectors.reddit import RedditConnector
from src.connectors.meta import MetaConnector
from src.policy.engine import PolicyEngine
import httpx


@pytest.fixture
def policy():
    return PolicyEngine()


@pytest.fixture
def mock_httpx_post(mocker):
    return mocker.patch("httpx.AsyncClient.post", new_callable=mocker.AsyncMock)


@pytest.fixture
def mock_httpx_get(mocker):
    return mocker.patch("httpx.AsyncClient.get", new_callable=mocker.AsyncMock)


@pytest.mark.asyncio
async def test_x_exceptions_and_stubs(policy, mock_httpx_post, mocker):
    x = XConnector(policy)
    req_mock = mocker.MagicMock()
    mock_httpx_post.side_effect = httpx.RequestError("X API Down", request=req_mock)

    # Publish exception
    with pytest.raises(httpx.RequestError):
        await x.publish("Hello")

    # Reply logic success
    mock_httpx_post.side_effect = None
    mock_resp = mocker.MagicMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"data": {"id": "reply_123"}}
    mock_httpx_post.return_value = mock_resp

    res_rep = await x.reply("t_1", "Hello")
    assert res_rep.ok is True
    assert res_rep.external_id == "reply_123"

    # Reply exception
    mock_httpx_post.side_effect = httpx.RequestError("X API Reply Down", request=req_mock)
    with pytest.raises(httpx.RequestError):
        await x.reply("t_1", "Hello")

    # Stubs
    res_mod = await x.moderate("id", "hide", "reason")
    assert res_mod.ok is False
    assert res_mod.error == "MVP Not Implemented"
    assert await x.sync_state("all") == {}
    assert await x.get_limits() == {}


@pytest.mark.asyncio
async def test_reddit_exceptions_and_stubs(policy, mock_httpx_post, mocker):
    r = RedditConnector(policy)
    # Auth success
    mock_resp_auth = mocker.MagicMock()
    mock_resp_auth.raise_for_status = lambda: None
    mock_resp_auth.json.return_value = {"access_token": "token_xyz", "expires_in": 3600}
    mock_httpx_post.return_value = mock_resp_auth

    await r._authenticate()
    assert r._token == "token_xyz"

    # Auth Failure
    req_mock = mocker.MagicMock()
    mock_httpx_post.side_effect = httpx.RequestError("Reddit Auth Down", request=req_mock)
    r._token = None
    with pytest.raises(Exception):
        await r._authenticate()

    mock_httpx_post.side_effect = None

    # Publish Success
    r._token = "valid"
    mock_resp_pub = mocker.MagicMock()
    mock_resp_pub.raise_for_status = lambda: None
    mock_resp_pub.json.return_value = {"json": {"data": {"name": "t3_post"}}}
    mock_httpx_post.return_value = mock_resp_pub

    res_pub = await r.publish("Hello Title", options={"subreddit": "test", "is_link": False})
    assert res_pub.ok is True

    res_pub_link = await r.publish("Title", options={"subreddit": "test", "is_link": True, "url": "http://x"})
    assert res_pub_link.ok is True

    # Publish Exception
    mock_httpx_post.side_effect = httpx.RequestError("Reddit Pub Down", request=req_mock)
    with pytest.raises(httpx.RequestError):
        await r.publish("Title", options={"subreddit": "test"})

    # Reply Exception
    with pytest.raises(httpx.RequestError):
        await r.reply("t_1", "reply")

    # Stubs
    res_mod = await r.moderate("id", "hide", "reason")
    assert res_mod.ok is False
    assert res_mod.error == "MVP Not Implemented"
    assert await r.sync_state("all") == {}
    assert await r.get_limits() == {}


@pytest.mark.asyncio
async def test_meta_exceptions_and_stubs(policy, mock_httpx_post, mock_httpx_get, mocker):
    m = MetaConnector(policy)

    # Publish FB Target
    mock_resp_pub = mocker.MagicMock()
    mock_resp_pub.raise_for_status = lambda: None
    mock_resp_pub.json.return_value = {"id": "fb_post_1"}
    mock_httpx_post.return_value = mock_resp_pub

    res_pub = await m.publish("FB Post", options={"target": "facebook"})
    assert res_pub.ok is True
    assert res_pub.external_id == "fb_post_1"

    # Publish Ig exceptions
    req_mock = mocker.MagicMock()
    mock_httpx_post.side_effect = httpx.RequestError("Meta API Down", request=req_mock)
    with pytest.raises(httpx.RequestError):
        await m.publish("Fail", options={"target": "facebook"})

    # Reply logic fb
    mock_httpx_post.side_effect = None
    mock_resp_rep = mocker.MagicMock()
    mock_resp_rep.raise_for_status = lambda: None
    mock_resp_rep.json.return_value = {"id": "fb_comment_1"}
    mock_httpx_post.return_value = mock_resp_rep

    res_rep_fb = await m.reply("thread_1", "Reply", options={"target": "facebook"})
    assert res_rep_fb.ok is True

    # Reply logic ig
    mock_resp_rep_ig = mocker.MagicMock()
    mock_resp_rep_ig.raise_for_status = lambda: None
    mock_resp_rep_ig.json.return_value = {"id": "ig_reply_1"}
    mock_httpx_post.return_value = mock_resp_rep_ig

    res_rep_ig = await m.reply("thread_1", "Reply", options={"target": "instagram"})
    assert res_rep_ig.ok is True

    # Reply Exception
    mock_httpx_post.side_effect = httpx.RequestError("Meta Reply Down", request=req_mock)
    with pytest.raises(httpx.RequestError):
        await m.reply("thread_1", "Reply", options={"target": "facebook"})

    # Stubs
    res_mod = await m.moderate("id", "hide", "reason")
    assert res_mod.ok is False
    assert res_mod.error == "MVP Not Implemented"
    assert await m.sync_state("all") == {}
    assert await m.get_limits() == {}
