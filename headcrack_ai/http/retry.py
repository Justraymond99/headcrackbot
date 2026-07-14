from __future__ import annotations

import time
from functools import wraps
from typing import Callable, TypeVar

from ..logging_config import get_logger
from ..settings import get_settings

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable)


def retry_http(
    attempts: int | None = None,
    backoff: float | None = None,
    exceptions: tuple[type[Exception], ...] = (OSError, TimeoutError),
) -> Callable[[F], F]:
    settings = get_settings()
    max_attempts = attempts or settings.http_retry_attempts
    base_backoff = backoff or settings.http_retry_backoff

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    sleep_s = base_backoff ** (attempt - 1)
                    logger.warning(
                        "HTTP call failed (attempt %s/%s): %s; retrying in %.1fs",
                        attempt,
                        max_attempts,
                        exc,
                        sleep_s,
                    )
                    time.sleep(sleep_s)
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
