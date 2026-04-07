from dataclasses import dataclass


@dataclass
class RiderState:
    rider_id: str
    is_logged_in: bool
    is_on_delivery: bool


class AppInterface:
    """Placeholder interface for future mobile app state integration."""

    def __init__(self) -> None:
        self._state = RiderState(rider_id="rider_001", is_logged_in=False, is_on_delivery=False)

    def get_rider_state(self) -> RiderState:
        return self._state

    def get_rider_id(self) -> str:
        return self._state.rider_id

    def get_delivery_status(self) -> bool:
        return self._state.is_on_delivery

    # Simulation controls for demo/testing.
    def simulate_login(self) -> None:
        self._state.is_logged_in = True

    def simulate_logout(self) -> None:
        self._state.is_logged_in = False
        self._state.is_on_delivery = False

    def simulate_delivery_start(self) -> None:
        if self._state.is_logged_in:
            self._state.is_on_delivery = True

    def simulate_delivery_stop(self) -> None:
        self._state.is_on_delivery = False
