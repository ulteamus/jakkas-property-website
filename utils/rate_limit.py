"""Simple in-process rate limiter for sensitive POST routes (serverless-friendly)."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, Deque, Dict, Optional, Tuple

from flask import jsonify, request

_lock = threading.Lock()
_buckets: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)


def _client_key() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.remote_addr or "unknown"


def check_rate_limit(scope: str, *, limit: int = 20, window: int = 60) -> Tuple[bool, int]:
    """Return (allowed, retry_after_seconds)."""
    now = time.time()
    key = (scope, _client_key())
    with _lock:
        q = _buckets[key]
        cutoff = now - window
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            retry = max(1, int(window - (now - q[0])))
            return False, retry
        q.append(now)
        return True, 0


def rate_limit(scope: str, *, limit: int = 20, window: int = 60, json_response: bool = True, methods: tuple = ("POST", "PUT", "PATCH", "DELETE")):
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if request.method not in methods:
                return fn(*args, **kwargs)
            allowed, retry = check_rate_limit(scope, limit=limit, window=window)
            if not allowed:
                if json_response or request.path.startswith("/api/"):
                    resp = jsonify(
                        {
                            "success": False,
                            "error": "rate_limited",
                            "message": "Too many requests. Please try again shortly.",
                            "retry_after": retry,
                        }
                    )
                    resp.status_code = 429
                    resp.headers["Retry-After"] = str(retry)
                    return resp
                from flask import abort

                abort(429)
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def reset_rate_limits() -> None:
    with _lock:
        _buckets.clear()
