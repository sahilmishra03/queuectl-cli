from datetime import datetime, timedelta
from app.services.retry import RetryService
from app.core import config_manager


def test_retry_delays():
    service = RetryService()
    now = datetime.utcnow()

    # Attempt 1 -> 2^1 = 2 seconds
    next_time = service.next_retry(1)
    diff = (next_time - now).total_seconds()
    assert 1.8 <= diff <= 2.2

    # Attempt 2 -> 2^2 = 4 seconds
    next_time = service.next_retry(2)
    diff = (next_time - now).total_seconds()
    assert 3.8 <= diff <= 4.2

    # Attempt 3 -> 2^3 = 8 seconds
    next_time = service.next_retry(3)
    diff = (next_time - now).total_seconds()
    assert 7.8 <= diff <= 8.2


def test_retry_custom_backoff(monkeypatch):
    monkeypatch.setattr(config_manager, "get", lambda k: 3 if k == "backoff-base" else config_manager.DEFAULT_CONFIG.get(k))
    service = RetryService()
    now = datetime.utcnow()

    # Attempt 1 with base 3 -> 3^1 = 3 seconds
    next_time = service.next_retry(1)
    diff = (next_time - now).total_seconds()
    assert 2.8 <= diff <= 3.2
