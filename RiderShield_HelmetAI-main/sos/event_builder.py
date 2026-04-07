import time
import uuid
from typing import Dict


def build_incident_event(
    rider_id: str,
    metadata: Dict,
    video_path: str,
    confidence: float,
    signals: Dict,
) -> Dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "ACCIDENT",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(metadata["timestamp"])),
        "gps": metadata["gps"],
        "digipin": metadata["digipin"],
        "video_path": video_path,
        "confidence": round(float(confidence), 4),
        "signals": signals,
        "source": "helmet_dashcam",
        "rider_id": rider_id,
    }
