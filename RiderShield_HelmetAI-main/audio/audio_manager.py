import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from audio.tts_engine import TTSEngine


PRIORITY_NAV = 0
PRIORITY_WARNING = 1
PRIORITY_COLLISION = 2


@dataclass(order=True)
class _AudioItem:
    sort_index: tuple = field(init=False, repr=False)
    priority: int
    sequence: int
    text: str
    kind: str
    force: bool = False

    def __post_init__(self) -> None:
        # Highest priority first, FIFO within same priority.
        self.sort_index = (-self.priority, self.sequence)


class AudioManager:
    """Priority audio queue with interruption, debounce, and nav resume behavior."""

    def __init__(self) -> None:
        self._queue: "queue.PriorityQueue[_AudioItem]" = queue.PriorityQueue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._tts = TTSEngine()

        self._seq = 0
        self._current_priority = PRIORITY_NAV
        self._current_kind = "navigation"
        self._state_lock = threading.Lock()

        self._cooldowns: Dict[str, float] = {
            "collision": 2.0,
            "warning": 3.0,
            "navigation": 5.0,
        }
        self._last_spoken_time: Dict[str, float] = {"collision": 0.0, "warning": 0.0, "navigation": 0.0}
        self._pending_resume_navigation: Optional[str] = None

    def start(self) -> None:
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._tts.stop()
        self._worker.join(timeout=2.0)

    def speak_navigation(self, text: str, force: bool = False) -> bool:
        return self._enqueue(text=text, kind="navigation", priority=PRIORITY_NAV, force=force)

    def speak_warning(self, text: str, resume_navigation_text: Optional[str] = None, force: bool = False) -> bool:
        enqueued = self._enqueue(text=text, kind="warning", priority=PRIORITY_WARNING, force=force)
        if enqueued and resume_navigation_text:
            self._pending_resume_navigation = resume_navigation_text
        return enqueued

    def speak_collision(self, text: str, resume_navigation_text: Optional[str] = None, force: bool = False) -> bool:
        enqueued = self._enqueue(text=text, kind="collision", priority=PRIORITY_COLLISION, force=force)
        if enqueued and resume_navigation_text:
            self._pending_resume_navigation = resume_navigation_text
        return enqueued

    def _enqueue(self, text: str, kind: str, priority: int, force: bool) -> bool:
        now = time.time()
        if not force:
            cooldown = self._cooldowns.get(kind, 0.0)
            if now - self._last_spoken_time.get(kind, 0.0) < cooldown:
                return False

        with self._state_lock:
            should_interrupt = priority > self._current_priority
            self._seq += 1
            item = _AudioItem(priority=priority, sequence=self._seq, text=text, kind=kind, force=force)

            if should_interrupt:
                self._tts.stop()
                if priority >= PRIORITY_WARNING:
                    self._drain_lower_priority(max_priority=priority)

            self._queue.put(item)
            return True

    def _drain_lower_priority(self, max_priority: int) -> None:
        kept = []
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item.priority >= max_priority:
                kept.append(item)
        for item in kept:
            self._queue.put(item)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            with self._state_lock:
                self._current_priority = item.priority
                self._current_kind = item.kind

            try:
                self._tts.speak_blocking(item.text)
                self._last_spoken_time[item.kind] = time.time()
            except RuntimeError:
                # Engine can throw while interrupted; safe to continue.
                pass
            finally:
                with self._state_lock:
                    self._current_priority = PRIORITY_NAV
                    self._current_kind = "navigation"

            if item.kind in ("collision", "warning") and self._pending_resume_navigation:
                resume_text = self._pending_resume_navigation
                self._pending_resume_navigation = None
                self.speak_navigation(resume_text, force=True)
