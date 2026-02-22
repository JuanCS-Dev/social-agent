from src.planner.scheduler import Scheduler
from datetime import datetime, timezone, timedelta


def test_scheduler_budget():
    s = Scheduler()
    assert s.can_operate("x") is True
    s.record_usage("x", 40)  # Uses full budget
    assert s.can_operate("x") is False


def test_scheduler_unknown_platform():
    s = Scheduler()
    assert s.can_operate("unknown_platform") is True  # MVP defaults to true


def test_scheduler_reset():
    s = Scheduler()
    s.record_usage("reddit", 50)
    assert s.can_operate("reddit") is False

    # Simulate a day passing
    s.current_day = datetime.now(timezone.utc).date() - timedelta(days=1)

    assert s.can_operate("reddit") is True
    assert s.usage_today["reddit"] == 0
