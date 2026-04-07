from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class RouteStep:
    instruction: str
    distance_m: float
    turn_type: str


def convert_digi_pin_to_coordinates(digi_pin: str) -> Tuple[float, float]:
    """
    Future integration point.
    For now returns Marina Beach coordinates while keeping the interface stable.
    """
    _ = digi_pin
    return 13.0500, 80.2824


def load_default_marina_route(origin: Tuple[float, float] = (13.0674, 80.2376)) -> Dict:
    destination = (13.0500, 80.2824)  # Marina Beach, Chennai

    steps: List[RouteStep] = [
        RouteStep("Go straight for 200 meters", 200.0, "straight"),
        RouteStep("Turn left toward Kamarajar Salai", 60.0, "left"),
        RouteStep("Continue for 500 meters", 500.0, "straight"),
        RouteStep("Turn right toward Marina Beach", 120.0, "right"),
        RouteStep("You are arriving at Marina Beach", 50.0, "arrive"),
    ]

    return {
        "origin": origin,
        "destination": destination,
        "destination_name": "Marina Beach, Chennai",
        "steps": steps,
        "provider": "mock",  # swap later with OSRM/ORS without changing manager API
    }
