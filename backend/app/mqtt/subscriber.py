import json
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pymongo import MongoClient

from app.config import settings


def start_mqtt():
    """Blocking MQTT loop — run in daemon thread."""
    mongo = MongoClient(settings.MONGO_URI)
    db = mongo.ridershield

    def on_connect(client, userdata, flags, rc, props=None):
        print(f"MQTT connected (rc={rc})")
        client.subscribe("ridershield/hfv/#")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            payload.setdefault("ts", datetime.now(timezone.utc).isoformat())
            payload["location"] = {
                "type": "Point",
                "coordinates": [payload.get("lng", 0), payload.get("lat", 0)],
            }
            payload.setdefault("proof_score", 0.0)
            payload.setdefault("verified", False)
            payload.setdefault("cross_rider_count", 1)
            db.hazard_vectors.insert_one(payload)
            print(f"HFV stored from MQTT: {payload.get('rider_id')}")
        except Exception as e:
            print(f"MQTT message error: {e}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_PORT, 60)
    client.loop_forever()
