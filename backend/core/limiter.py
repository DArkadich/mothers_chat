import os
import time
from threading import Lock
from fastapi import Request, HTTPException, status

RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
WINDOW = 60  # seconds

class _InMemoryLimiter:
    def __init__(self, limit=RATE_LIMIT, window=WINDOW):
        self.limit = limit
        self.window = window
        self.store = {}  # key -> (window_start, count)
        self.lock = Lock()

    def allowed(self, key: str) -> bool:
        now = int(time.time())
        with self.lock:
            start, cnt = self.store.get(key, (now, 0))
            if now - start >= self.window:
                self.store[key] = (now, 1)
                return True
            if cnt < self.limit:
                self.store[key] = (start, cnt + 1)
                return True
            return False

limiter = _InMemoryLimiter()

async def rate_limit_dep(request: Request):
    key = request.client.host if request.client else "anon"
    if not limiter.allowed(key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    return True
