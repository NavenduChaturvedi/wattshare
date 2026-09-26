"""The live simulation clock: which simulated hour it should be, right now.

At speed 1 the simulation follows real time in the configured timezone -- open
the dashboard at 15:20 IST and the 15:00 hour is open for trading. At speed > 1
time runs faster from the moment the server started (e.g. 60 = one simulated
hour per real minute), for demos.

The clock is stateless arithmetic over the wall clock, so nothing has to run in
the background: whoever asks (every API request does) can compare the engine's
tick count with target_ticks() and catch it up. That matters on free hosting,
which sleeps idle servers and would kill a timer thread anyway.
"""

import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SECONDS_PER_HOUR = 3600


def utc_now() -> datetime:
    """Indirection so tests can freeze time."""
    return datetime.now(timezone.utc)


class LiveClock:
    def __init__(self, tz: str, speed: float = 1.0):
        if speed <= 0:
            raise ValueError("clock speed must be positive")
        self.zone = ZoneInfo(tz)
        self.speed = speed
        self.started_at = utc_now()
        local = self.started_at.astimezone(self.zone)
        # Tick 0 is midnight (local) on the day the server started; the engine
        # starts there and catches up to the current hour straight away.
        self._start_offset_hours = local.hour + local.minute / 60 + local.second / SECONDS_PER_HOUR

    def _sim_hours(self, now: datetime) -> float:
        elapsed = max((now - self.started_at).total_seconds(), 0.0) / SECONDS_PER_HOUR
        return self._start_offset_hours + elapsed * self.speed

    def target_ticks(self, now: datetime = None) -> int:
        """How many hourly ticks since the start day's midnight the simulation should have run."""
        return math.floor(self._sim_hours(now or utc_now()) + 1e-9)

    def seconds_to_next_hour(self, now: datetime = None) -> float:
        """Real seconds until the next simulated hour opens."""
        sim = self._sim_hours(now or utc_now())
        remaining_sim_hours = math.floor(sim + 1e-9) + 1 - sim
        return round(remaining_sim_hours / self.speed * SECONDS_PER_HOUR, 1)

    def local_time(self, now: datetime = None) -> datetime:
        """The simulated wall-clock time (equals real local time at speed 1)."""
        sim = self._sim_hours(now or utc_now())
        midnight = self.started_at.astimezone(self.zone).replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight + timedelta(hours=sim)
