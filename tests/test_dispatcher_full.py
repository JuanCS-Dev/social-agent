import pytest
from src.agent.act import dispatcher
from src.core.contracts import Platform
from src.connectors.x import XConnector
from src.connectors.meta import MetaConnector
from src.connectors.reddit import RedditConnector

@pytest.fixture
def mock_scheduler(mocker):
    s = mocker.patch("src.agent.act.scheduler.can_operate", return_value=True)
    mocker.patch("src.agent.act.scheduler.record_usage")
    return s

@pytest.mark.asyncio
@pytest.mark.parametrize("platform,connector_cls", [
    (Platform.X, XConnector),
    (Platform.FACEBOOK, MetaConnector),
    (Platform.INSTAGRAM, MetaConnector),
    (Platform.REDDIT, RedditConnector)
])
async def test_dispatcher_publish_all_platforms(mock_scheduler, mocker, platform, connector_cls):
    mock_publish = mocker.patch.object(connector_cls, "publish")
    
    # Needs to match what act.py does
    await dispatcher.execute_publish(platform, "test content")
    mock_publish.assert_called_once()
    
@pytest.mark.asyncio
@pytest.mark.parametrize("platform,connector_cls", [
    (Platform.X, XConnector),
    (Platform.FACEBOOK, MetaConnector),
    (Platform.INSTAGRAM, MetaConnector),
    (Platform.REDDIT, RedditConnector)
])
async def test_dispatcher_reply_all_platforms(mock_scheduler, mocker, platform, connector_cls):
    mock_reply = mocker.patch.object(connector_cls, "reply")
    await dispatcher.execute_reply(platform, "thread_1", "reply content")
    mock_reply.assert_called_once()
