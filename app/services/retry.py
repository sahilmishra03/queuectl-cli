from datetime import datetime, timedelta


class RetryService:

    def next_retry(self, attempts: int) -> datetime:
        delay = 2 ** attempts
        return datetime.utcnow() + timedelta(seconds=delay)
