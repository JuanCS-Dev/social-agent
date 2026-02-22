from datetime import datetime, timezone, timedelta, date
from src.core.logger import log


class Scheduler:
    def __init__(self):
        # MVP: in-memory budget tracking per platform.
        # Production would use Redis/DB for distributed workers.
        self.base_daily_budget = {
            "reddit": 50,
            "x": 40,
            "instagram": 90,  # Keep under 100/24h per docs to be safe
            "facebook": 200,
        }
        self.daily_budget = dict(self.base_daily_budget)
        self.usage_today = {"reddit": 0, "x": 0, "instagram": 0, "facebook": 0}
        self.results_today = {
            "reddit": {"ok": 0, "fail": 0, "publish": 0, "reply": 0},
            "x": {"ok": 0, "fail": 0, "publish": 0, "reply": 0},
            "instagram": {"ok": 0, "fail": 0, "publish": 0, "reply": 0},
            "facebook": {"ok": 0, "fail": 0, "publish": 0, "reply": 0},
        }
        self.last_action_at: dict[str, dict[str, datetime | None]] = {
            "reddit": {"publish": None, "reply": None},
            "x": {"publish": None, "reply": None},
            "instagram": {"publish": None, "reply": None},
            "facebook": {"publish": None, "reply": None},
        }
        self.failure_streak = {"reddit": 0, "x": 0, "instagram": 0, "facebook": 0}
        self.backoff_until: dict[str, datetime | None] = {
            "reddit": None,
            "x": None,
            "instagram": None,
            "facebook": None,
        }
        self.last_reflection_day: date | None = None
        self.current_day = datetime.now(timezone.utc).date()

    def _reset_if_needed(self):
        today = datetime.now(timezone.utc).date()
        if today > self.current_day:
            self.daily_budget = dict(self.base_daily_budget)
            for k in self.usage_today:
                self.usage_today[k] = 0
            for platform, counters in self.results_today.items():
                for key in counters:
                    self.results_today[platform][key] = 0
            self.current_day = today

    def can_operate(self, platform: str, cost: int = 1) -> bool:
        """Checks if there is enough budget to operate."""
        self._reset_if_needed()
        if platform not in self.usage_today:
            return True  # Unknown platform, allow for MVP

        now = datetime.now(timezone.utc)
        blocked_until = self.backoff_until.get(platform)
        if blocked_until and blocked_until > now:
            return False

        return (self.usage_today[platform] + cost) <= self.daily_budget[platform]

    def record_usage(self, platform: str, cost: int = 1):
        """Records platform usage after a successful action."""
        self._reset_if_needed()
        if platform in self.usage_today:
            self.usage_today[platform] += cost
            log.info(f"Recorded usage for {platform}: +{cost}. Total today: {self.usage_today[platform]}/{self.daily_budget[platform]}")

    def mark_action(self, platform: str, action_type: str):
        self._reset_if_needed()
        if platform in self.last_action_at and action_type in self.last_action_at[platform]:
            self.last_action_at[platform][action_type] = datetime.now(timezone.utc)

    def can_publish_now(self, platform: str, min_interval_minutes: int) -> bool:
        self._reset_if_needed()
        if not self.can_operate(platform):
            return False
        if platform not in self.last_action_at:
            return True

        last_publish = self.last_action_at[platform]["publish"]
        if not last_publish:
            return True

        elapsed = datetime.now(timezone.utc) - last_publish
        return elapsed >= timedelta(minutes=max(1, min_interval_minutes))

    def record_result(self, platform: str, ok: bool, action_type: str | None = None):
        """Autoregulation: repeated failures trigger temporary platform backoff."""
        if platform in self.results_today:
            if ok:
                self.results_today[platform]["ok"] += 1
            else:
                self.results_today[platform]["fail"] += 1
            if action_type in {"publish", "reply"}:
                self.results_today[platform][action_type] += 1

        if platform not in self.failure_streak:
            return
        if ok:
            self.failure_streak[platform] = 0
            self.backoff_until[platform] = None
            return

        self.failure_streak[platform] += 1
        if self.failure_streak[platform] >= 3:
            self.backoff_until[platform] = datetime.now(timezone.utc) + timedelta(minutes=30)
            self.failure_streak[platform] = 0
            log.warning(f"Platform {platform} paused for 30 minutes due to repeated failures.")

    def should_run_daily_reflection(self) -> bool:
        today = datetime.now(timezone.utc).date()
        return self.last_reflection_day != today

    def mark_daily_reflection(self):
        self.last_reflection_day = datetime.now(timezone.utc).date()

    def snapshot(self) -> dict[str, object]:
        def _serialize(value: datetime | None) -> str | None:
            return value.isoformat() if value else None

        success_rate: dict[str, float] = {}
        for platform, counters in self.results_today.items():
            total = counters["ok"] + counters["fail"]
            success_rate[platform] = round(counters["ok"] / total, 6) if total > 0 else 0.0

        return {
            "current_day": self.current_day.isoformat(),
            "daily_budget": dict(self.daily_budget),
            "usage_today": dict(self.usage_today),
            "results_today": {platform: dict(counters) for platform, counters in self.results_today.items()},
            "success_rate": success_rate,
            "backoff_until": {k: _serialize(v) for k, v in self.backoff_until.items()},
            "last_action_at": {platform: {action: _serialize(ts) for action, ts in action_map.items()} for platform, action_map in self.last_action_at.items()},
        }


# Singleton for simple DI MVP
scheduler = Scheduler()
