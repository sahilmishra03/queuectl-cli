from datetime import datetime, timedelta

from app.core import config_manager


class RetryService:

    def __init__(self):
        self.backoff_base = config_manager.get("backoff-base")

    def next_retry(self, attempts: int) -> datetime:
        delay = self.backoff_base ** attempts
        return datetime.utcnow() + timedelta(seconds=delay)
