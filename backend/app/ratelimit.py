import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.config import get_settings
from app.errors import TooManyRequests


class FailureLimiter:
    """Ограничивает число неудачных попыток для ключа (например, IP) за окно времени"""

    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> int:
        q = self._failures[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if not q:
            self._failures.pop(key, None)
        return len(q)

    def check(self, key: str) -> None:
        """Бросает 429, если лимит неудачных попыток исчерпан"""
        with self._lock:
            if self._prune(key, time.monotonic()) >= self.max_failures:
                raise TooManyRequests("Слишком много неудачных попыток. Попробуйте позже.")

    def add_failure(self, key: str) -> None:
        with self._lock:
            self._failures[key].append(time.monotonic())

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


# Лимитеры живут в памяти одного процесса: при нескольких воркерах лимит считается на каждый отдельно
code_limiter = FailureLimiter(max_failures=10, window_seconds=600)
admin_limiter = FailureLimiter(max_failures=10, window_seconds=600)


def client_ip(request: Request) -> str:
    """
    IP клиента. X-Forwarded-For доверяем только в той части, которую дописали наши прокси:
    берём адрес, добавленный самым внешним из TRUSTED_PROXY_HOPS прокси (всё левее клиент мог
    подделать). Если запрос пришёл мимо прокси — адрес TCP-соединения.
    """
    direct = request.client.host if request.client else "unknown"
    hops = get_settings().TRUSTED_PROXY_HOPS
    forwarded = request.headers.get("x-forwarded-for")
    if hops <= 0 or not forwarded:
        return direct
    entries = [e.strip() for e in forwarded.split(",") if e.strip()]
    if len(entries) < hops:
        return direct
    return entries[-hops]
