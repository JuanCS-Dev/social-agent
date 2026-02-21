from datetime import datetime, timezone
from src.core.logger import log

class Scheduler:
    def __init__(self):
        # MVP: simple in-memory budget tracking per platform
        # Production would use Redis or DB to share state across workers
        self.daily_budget = {
            "reddit": 50,
            "x": 40,
            "instagram": 90, # Keep under 100/24h per docs to be safe
            "facebook": 200
        }
        self.usage_today = {
            "reddit": 0,
            "x": 0,
            "instagram": 0,
            "facebook": 0
        }
        self.current_day = datetime.now(timezone.utc).date()

    def _reset_if_needed(self):
        today = datetime.now(timezone.utc).date()
        if today > self.current_day:
            for k in self.usage_today:
                self.usage_today[k] = 0
            self.current_day = today

    def can_operate(self, platform: str, cost: int = 1) -> bool:
        """Checks if there is enough budget to operate."""
        self._reset_if_needed()
        if platform not in self.usage_today:
            return True # Unknown platform, allow for MVP
        
        return (self.usage_today[platform] + cost) <= self.daily_budget[platform]

    def record_usage(self, platform: str, cost: int = 1):
        """Records platform usage after a successful action."""
        self._reset_if_needed()
        if platform in self.usage_today:
            self.usage_today[platform] += cost
            log.info(f"Recorded usage for {platform}: +{cost}. Total today: {self.usage_today[platform]}/{self.daily_budget[platform]}")

# Singleton for simple DI MVP
scheduler = Scheduler()
