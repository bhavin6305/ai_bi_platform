import pytest

from api.rate_limit import FixedWindowRateLimiter, RedisRateLimiter, ResilientRateLimiter, get_rate_limiter


def test_rate_limiter_rejects_requests_after_limit():
    now = [100.0]
    limiter = FixedWindowRateLimiter(2, 60, clock=lambda: now[0])

    assert limiter.check("client-1")[0] is True
    assert limiter.check("client-1")[0] is True
    allowed, retry_after = limiter.check("client-1")

    assert allowed is False
    assert retry_after == 60


def test_rate_limiter_resets_after_window():
    now = [100.0]
    limiter = FixedWindowRateLimiter(1, 60, clock=lambda: now[0])

    assert limiter.check("client-1")[0] is True
    assert limiter.check("client-1")[0] is False
    now[0] = 160.0
    assert limiter.check("client-1")[0] is True


def test_redis_rate_limiter_sets_expiry_on_first_request():
    class FakeRedis:
        def __init__(self):
            self.count = 0
            self.expiry = None

        def incr(self, key):
            self.count += 1
            return self.count

        def expire(self, key, seconds):
            self.expiry = seconds

        def ttl(self, key):
            return self.expiry or 0

    redis_client = FakeRedis()
    limiter = RedisRateLimiter(redis_client, limit=2, window_seconds=60)

    allowed, retry_after = limiter.check("client-1")

    assert allowed is True
    assert retry_after == 60
    assert redis_client.expiry == 60


def test_rate_limiter_requires_redis_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(ValueError, match="REDIS_URL"):
        get_rate_limiter()


def test_rate_limiter_uses_local_fallback_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("REDIS_URL", raising=False)

    assert isinstance(get_rate_limiter(), FixedWindowRateLimiter)


def test_resilient_limiter_falls_back_when_redis_drops(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")

    class BrokenRedis:
        def incr(self, key):
            raise ConnectionError("Redis stopped")

    limiter = ResilientRateLimiter(
        RedisRateLimiter(BrokenRedis(), limit=1, window_seconds=60),
        FixedWindowRateLimiter(limit=1, window_seconds=60),
    )

    assert limiter.check("client-1")[0] is True
    assert limiter.check("client-1")[0] is False