# adaptive_pacer.py
import time, random
from collections import deque

# Tunables: conservative base; bump when things are "green"
BASE_RPM = 45       # Phase 1 optimization: 33% faster (was 30)
MAX_RPM  = 90       # Phase 1 optimization: 33% faster (was 60)
WINDOW_SEC = 300    # 5 minutes for faster adaptation (37.5% faster)
MAX_429 = 1
MAX_JS  = 1

_events = deque()  # (ts, kind) where kind in {"ok","429","js"}

def mark(kind: str):
    now = time.time()
    _events.append((now, kind))
    while _events and now - _events[0][0] > WINDOW_SEC:
        _events.popleft()

def target_rpm():
    now = time.time()
    last = [k for (ts,k) in _events if now - ts <= WINDOW_SEC]
    if last.count("429") <= MAX_429 and last.count("js") <= MAX_JS:
        return MAX_RPM
    return BASE_RPM

def pace_sleep():
    rpm = target_rpm()
    base = 60.0 / max(1, rpm)
    jitter = 0.4 + (random.random()*0.8)
    time.sleep(base + jitter)

def next_delay(success_rate_10m: float, last_errors: int) -> float:
    """Enhanced delay calculation with fast-on-clean / slow-on-wobble behavior."""
    if last_errors > 0 or (success_rate_10m is not None and success_rate_10m < 0.92):
        return random.uniform(2.0, 3.5)
    if success_rate_10m is not None and success_rate_10m > 0.98:
        return random.uniform(0.3, 0.8)
    if success_rate_10m is not None and success_rate_10m > 0.95:
        return random.uniform(0.8, 1.5)
    return random.uniform(1.5, 2.2)
