# app/core/business.py
from __future__ import annotations
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Edmonton")

# 0=Mon .. 6=Sun
BUSINESS_HOURS = {
    0: (time(9, 0), time(17, 0)),  # Mon
    1: (time(9, 0), time(17, 0)),  # Tue
    2: (time(9, 0), time(17, 0)),  # Wed
    3: (time(9, 0), time(17, 0)),  # Thu
    4: (time(9, 0), time(17, 0)),  # Fri
    5: (time(9, 0), time(14, 0)),  # Sat (short)
    6: None,                       # Sun (closed)
}

def is_within_hours(dt_local: datetime) -> bool:
    wnd = BUSINESS_HOURS.get(dt_local.weekday())
    if not wnd:
        return False
    start, end = wnd
    t = dt_local.time()
    return start <= t <= end

def next_opening(after_local: datetime) -> datetime:
    cur = after_local
    for _ in range(14):  # look up to 2 weeks out
        wnd = BUSINESS_HOURS.get(cur.weekday())
        if wnd:
            start, end = wnd
            # same-day next opening if not past closing
            candidate = cur.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
            if cur.time() <= end:
                return candidate
        # move to next day 9am
        cur = (cur + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    return after_local  # fallback (shouldn’t hit often)
