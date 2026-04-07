import time
from dataclasses import dataclass
from enum import Enum


class IncidentState(str, Enum):
    IDLE = "IDLE"
    SUSPICIOUS = "SUSPICIOUS"
    CONFIRMED = "CONFIRMED"
    RECOVERY = "RECOVERY"


@dataclass
class StateOutput:
    state: IncidentState
    transitioned: bool
    confirmed: bool


class IncidentStateMachine:
    """Temporal state machine to suppress one-frame and repeated triggers."""

    def __init__(
        self,
        suspicious_frames_required: int = 5,
        confirmation_threshold: float = 0.72,
        recovery_seconds: float = 12.0,
    ) -> None:
        self.suspicious_frames_required = suspicious_frames_required
        self.confirmation_threshold = confirmation_threshold
        self.recovery_seconds = recovery_seconds

        self.state = IncidentState.IDLE
        self._suspicious_count = 0
        self._recovery_until = 0.0

    def update(self, suspicious_now: bool, confidence: float, timestamp: float) -> StateOutput:
        prev = self.state

        if self.state == IncidentState.RECOVERY:
            if timestamp >= self._recovery_until:
                self.state = IncidentState.IDLE
            return StateOutput(state=self.state, transitioned=(self.state != prev), confirmed=False)

        if suspicious_now:
            self._suspicious_count += 1
        else:
            self._suspicious_count = max(0, self._suspicious_count - 1)

        if self.state == IncidentState.IDLE and self._suspicious_count > 0:
            self.state = IncidentState.SUSPICIOUS

        confirmed = (
            self.state in (IncidentState.SUSPICIOUS, IncidentState.IDLE)
            and self._suspicious_count >= self.suspicious_frames_required
            and confidence >= self.confirmation_threshold
        )

        if confirmed:
            self.state = IncidentState.CONFIRMED
            # Immediate transition to recovery after confirmation edge.
            self._recovery_until = timestamp + self.recovery_seconds
            self.state = IncidentState.RECOVERY
            self._suspicious_count = 0
            return StateOutput(state=IncidentState.CONFIRMED, transitioned=True, confirmed=True)

        if self.state == IncidentState.SUSPICIOUS and self._suspicious_count == 0:
            self.state = IncidentState.IDLE

        return StateOutput(state=self.state, transitioned=(self.state != prev), confirmed=False)
