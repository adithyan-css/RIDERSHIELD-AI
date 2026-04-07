import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import httpx
import paho.mqtt.publish as mqtt_publish
from motor.motor_asyncio import AsyncIOMotorClient
from websockets.asyncio.client import connect as ws_connect


API_BASE = os.getenv("RIDERSHIELD_API_BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("RIDERSHIELD_API_KEY", "ridershield-dev-key")
MONGO_URI = os.getenv("RIDERSHIELD_MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("RIDERSHIELD_MONGO_DB", "ridershield")
MQTT_HOST = os.getenv("RIDERSHIELD_MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("RIDERSHIELD_MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("RIDERSHIELD_MQTT_TOPIC", "rider/events")


def _make_event(event_type: str, rider_id: str) -> dict:
    event_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "rider_id": rider_id,
        "timestamp": now_iso,
        "location": {"lat": 11.0168, "lng": 76.9558},
        "event_type": event_type,
        "confidence": 0.86,
        "metadata": {
            "event_id": event_id,
            "hazard_type": "traffic",
            "source": "e2e_test",
        },
    }


async def _wait_for_ws_events(expected_event_ids: set[str], timeout_s: float = 15.0) -> list[dict]:
    ws_url = API_BASE.replace("http://", "ws://").replace("https://", "wss://") + "/ws/events"
    received: list[dict] = []

    async with ws_connect(ws_url) as ws:
        async def _reader() -> None:
            while expected_event_ids:
                raw = await ws.recv()
                data = json.loads(raw)
                if data.get("type") != "AI_EVENT":
                    continue

                payload = data.get("payload") or {}
                metadata = payload.get("metadata") or {}
                event_id = metadata.get("event_id")
                if event_id in expected_event_ids:
                    expected_event_ids.remove(event_id)
                    received.append(data)

        await asyncio.wait_for(_reader(), timeout=timeout_s)
    return received


async def _assert_db_events(event_ids: list[str]) -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    try:
        for event_id in event_ids:
            doc = await db.ai_events.find_one({"metadata.event_id": event_id})
            if not doc:
                raise AssertionError(f"Missing ai_events document for event_id={event_id}")
    finally:
        client.close()


async def main() -> None:
    rider_id = "e2e_rider"
    http_event = _make_event("hazard", rider_id)
    mqtt_event = _make_event("collision_risk", rider_id)
    expected_ids = {
        http_event["metadata"]["event_id"],
        mqtt_event["metadata"]["event_id"],
    }

    ws_task = asyncio.create_task(_wait_for_ws_events(set(expected_ids)))

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{API_BASE}/api/ai/event",
            headers={"x-api-key": API_KEY},
            json=http_event,
        )
        response.raise_for_status()

    mqtt_publish.single(
        topic=MQTT_TOPIC,
        payload=json.dumps(mqtt_event),
        hostname=MQTT_HOST,
        port=MQTT_PORT,
        qos=1,
        retain=False,
    )

    ws_messages = await ws_task
    if len(ws_messages) < 2:
        raise AssertionError("Expected 2 AI_EVENT websocket messages")

    await _assert_db_events(list(expected_ids))
    print("E2E PASS: HTTP+MQTT ingestion, DB persistence, and websocket broadcast verified")


if __name__ == "__main__":
    asyncio.run(main())