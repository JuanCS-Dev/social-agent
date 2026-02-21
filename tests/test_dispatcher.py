import pytest
import httpx
from src.agent.act import dispatcher
from src.core.contracts import Platform
from src.planner.scheduler import scheduler

@pytest.mark.asyncio
async def test_dispatcher_publish_budget_exceeded(mocker):
    mocker.patch.object(scheduler, "can_operate", return_value=False)
    
    res = await dispatcher.execute_publish(Platform.X, "test")
    assert res.ok is False
    assert res.error == "Rate budget exceeded"

@pytest.mark.asyncio
async def test_dispatcher_reply_budget_exceeded(mocker):
    mocker.patch.object(scheduler, "can_operate", return_value=False)
    
    res = await dispatcher.execute_reply(Platform.X, "t1", "test")
    assert res.ok is False
    assert res.error == "Rate budget exceeded"

@pytest.mark.asyncio
async def test_dispatcher_invalid_platform_publish(mocker):
    mocker.patch.object(scheduler, "can_operate", return_value=True)
    class FakePlatform:
        value = "fake"
    
    with pytest.raises(ValueError):
        await dispatcher.execute_publish(FakePlatform(), "test") # type: ignore

@pytest.mark.asyncio
async def test_dispatcher_invalid_platform_reply(mocker):
    mocker.patch.object(scheduler, "can_operate", return_value=True)
    class FakePlatform:
        value = "fake"
    
    with pytest.raises(ValueError):
        await dispatcher.execute_reply(FakePlatform(), "t1", "test") # type: ignore

@pytest.mark.asyncio
async def test_dispatcher_publish_exception(mocker):
    mocker.patch.object(scheduler, "can_operate", return_value=True)
    mock_x = mocker.patch("src.connectors.x.XConnector.publish", new_callable=mocker.AsyncMock)
    mock_x.side_effect = httpx.HTTPStatusError("Bad Req", request=mocker.Mock(), response=mocker.Mock())
    
    res = await dispatcher.execute_publish(Platform.X, "test")
    assert res.ok is False
    assert "Bad Req" in str(res.error)

@pytest.mark.asyncio
async def test_dispatcher_reply_exception(mocker):
    mocker.patch.object(scheduler, "can_operate", return_value=True)
    mock_x = mocker.patch("src.connectors.x.XConnector.reply", new_callable=mocker.AsyncMock)
    mock_x.side_effect = httpx.HTTPStatusError("Bad Req", request=mocker.Mock(), response=mocker.Mock())
    
    res = await dispatcher.execute_reply(Platform.X, "t1", "test")
    assert res.ok is False
    assert "Bad Req" in str(res.error)
