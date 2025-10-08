# adaptive_pacer.py
import time, random
from collections import deque

# Tunables: conservative base; bump when things are "green"
BASE_RPM = 22
MAX_RPM  = 34
WINDOW_SEC = 600  # last 10 minutes
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
