"""Continuous interval screen capture service."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional


class ContinuousCapture:
    """Captures screenshots at a fixed interval while active."""

    def __init__(self, capture_fn: Callable[[], dict[str, Any]]) -> None:
        self._capture_fn = capture_fn
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._interval = 5.0
        self._count = 0
        self.logger = logging.getLogger("shadowforge.capture")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def capture_count(self) -> int:
        return self._count

    @property
    def interval(self) -> float:
        return self._interval

    def start(self, interval_sec: float = 5.0) -> None:
        if self._running:
            self.stop()
        self._interval = max(1.0, float(interval_sec))
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.logger.info("Continuous capture started (every %.1fs)", self._interval)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._interval + 2)
            self._thread = None
        self.logger.info("Continuous capture stopped (%d total)", self._count)

    def _loop(self) -> None:
        while self._running:
            try:
                self._capture_fn()
                self._count += 1
            except Exception as exc:
                self.logger.error("Capture failed: %s", exc)
            deadline = time.time() + self._interval
            while self._running and time.time() < deadline:
                time.sleep(0.1)

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "interval_sec": self._interval,
            "capture_count": self._count,
        }