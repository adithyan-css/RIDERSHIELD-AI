import uuid
from datetime import datetime, timezone
from typing import Dict


def build_incident_event(
    rider_id: str,
    metadata: Dict,
    video_path: str,
    confidence: float,
    signals: Dict,
) -> Dict:
    timestamp = datetime.fromtimestamp(float(metadata["timestamp"]), tz=timezone.utc).isoformat()
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "ACCIDENT",
        "timestamp": timestamp,
        "gps": metadata["gps"],
        "digipin": metadata["digipin"],
        "video_path": video_path,
        "confidence": round(float(confidence), 4),
        "signals": signals,
        "source": "helmet_dashcam",
        "rider_id": rider_id,
    }
