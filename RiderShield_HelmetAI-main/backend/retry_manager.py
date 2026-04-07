import json
import os
import threading
import time
from collections import deque
from typing import Callable, Deque, Dict, Tuple


class RetryManager:
    """Background retry queue with local persistence fallback."""

    def __init__(self, fallback_dir: str = "failed_events", retry_interval: float = 2.0) -> None:
        self.retry_interval = retry_interval
        self._queue: Deque[Tuple[Dict, int]] = deque()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._sender: Callable[[Dict], bool] = lambda _e: True
        self.fallback_dir = fallback_dir
        os.makedirs(self.fallback_dir, exist_ok=True)

    def start(self, sender: Callable[[Dict], bool]) -> None:
        self._sender = sender
        if not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._stop_event.clear()
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def enqueue(self, event: Dict, attempt: int = 0) -> None:
        with self._lock:
            self._queue.append((event, attempt))

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            item = None
            with self._lock:
                if self._queue:
                    item = self._queue.popleft()

            if item is None:
                time.sleep(0.2)
                continue

            event, attempt = item
            ok = self._sender(event)
            if ok:
                continue

            if attempt >= 3:
                self._persist_failed(event)
            else:
                time.sleep(self.retry_interval)
                self.enqueue(event, attempt=attempt + 1)

    def _persist_failed(self, event: Dict) -> None:
        event_id = event.get("event_id", f"failed_{int(time.time())}")
        path = os.path.join(self.fallback_dir, f"{event_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(event, f, indent=2)
        print(f"RetryManager persisted failed event: {path}")
