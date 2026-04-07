import time
from typing import Dict, Optional

from navigation.route_loader import RouteStep


class NavigationManager:
    """Simulated turn-by-turn progression manager."""

    def __init__(self, route: Dict, step_interval_seconds: float = 7.0) -> None:
        self.route = route
        self.steps = list(route["steps"])
        self.step_interval_seconds = step_interval_seconds
        self.current_step_idx = -1
        self.last_step_ts = 0.0
        self.started = False
        self.completed = False

    def start(self, now: Optional[float] = None) -> str:
        if now is None:
            now = time.time()
        self.started = True
        self.completed = False
        self.current_step_idx = -1
        self.last_step_ts = now
        return f"Starting navigation to {self.route['destination_name']}"

    def tick(self, now: float) -> Optional[RouteStep]:
        if not self.started or self.completed:
            return None

        if self.current_step_idx < 0:
            self.current_step_idx = 0
            self.last_step_ts = now
            return self.steps[self.current_step_idx]

        if now - self.last_step_ts < self.step_interval_seconds:
            return None

        self.current_step_idx += 1
        self.last_step_ts = now

        if self.current_step_idx >= len(self.steps):
            self.completed = True
            return None

        return self.steps[self.current_step_idx]

    def current_instruction_text(self) -> str:
        if self.current_step_idx < 0 or self.current_step_idx >= len(self.steps):
            return "Continue on current route"
        return self.steps[self.current_step_idx].instruction

    def force_next_step(self, now: float) -> Optional[RouteStep]:
        self.last_step_ts = 0.0
        return self.tick(now)
