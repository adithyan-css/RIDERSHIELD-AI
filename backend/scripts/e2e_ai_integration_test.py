import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import paho.mqtt.publish as mqtt_publish
from motor.motor_asyncio import AsyncIOMotorClient

try:
    from websockets.asyncio.client import connect as ws_connect
except Exception:  # websockets<=12 compatibility
    from websockets import connect as ws_connect


API_BASE = os.getenv("RIDERSHIELD_API_BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("RIDERSHIELD_API_KEY", os.getenv("AI_EVENT_API_KEY", "ridershield-dev-key"))
MONGO_URI = os.getenv("RIDERSHIELD_MONGO_URI", os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"))
ALT_MONGO_URI = os.getenv("RIDERSHIELD_MONGO_URI_ALT", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("RIDERSHIELD_MONGO_DB", "ridershield")
MQTT_HOST = os.getenv("RIDERSHIELD_MQTT_HOST", os.getenv("MQTT_BROKER_HOST", "127.0.0.1"))
MQTT_PORT = int(os.getenv("RIDERSHIELD_MQTT_PORT", os.getenv("MQTT_PORT", "1883")))
MQTT_TOPIC = os.getenv("RIDERSHIELD_MQTT_TOPIC", os.getenv("MQTT_TOPIC_AI_EVENTS", "rider/events"))


def _mongo_uri_candidates() -> list[str]:
    candidates = [MONGO_URI]
    if ALT_MONGO_URI and ALT_MONGO_URI not in candidates:
        candidates.append(ALT_MONGO_URI)
    return [item for item in candidates if item]


async def _available_mongo_dbs() -> tuple[list[AsyncIOMotorClient], list]:
    clients: list[AsyncIOMotorClient] = []
    dbs = []

    for uri in _mongo_uri_candidates():
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=1500)
        try:
            await client.admin.command("ping")
            clients.append(client)
            dbs.append(client[MONGO_DB])
        except Exception:
            client.close()

    if not dbs:
        raise AssertionError("No reachable MongoDB instance for E2E verification")
    return clients, dbs


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


def _ws_url(path: str) -> str:
    base = API_BASE.rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_base}{path}"


async def _wait_for_ws_events(
    ws_url: str,
    expected_event_ids: set[str],
    timeout_s: float = 15.0,
    init_payload: dict[str, Any] | None = None,
) -> list[dict]:
    received: list[dict] = []

    async with ws_connect(ws_url) as ws:
        if init_payload is not None:
            await ws.send(json.dumps(init_payload))

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
    clients, dbs = await _available_mongo_dbs()
    try:
        for event_id in event_ids:
            found = False
            for _ in range(20):
                for db in dbs:
                    doc = await db.ai_events.find_one({"metadata.event_id": event_id})
                    if doc:
                        found = True
                        break
                if found:
                    break
                await asyncio.sleep(0.4)
            if not found:
                raise AssertionError(f"Missing ai_events document for event_id={event_id}")
    finally:
        for client in clients:
            client.close()


async def _assert_single_record(event_id: str) -> None:
    clients, dbs = await _available_mongo_dbs()
    try:
        best_count = 0
        for _ in range(20):
            counts = [await db.ai_events.count_documents({"metadata.event_id": event_id}) for db in dbs]
            best_count = max(counts) if counts else 0
            if best_count == 1:
                return
            await asyncio.sleep(0.4)
        raise AssertionError(f"Expected 1 record for event_id={event_id}, found {best_count}")
    finally:
        for client in clients:
            client.close()


async def main() -> None:
    rider_id = "e2e_rider"
    http_event = _make_event("hazard", rider_id)
    mqtt_event = _make_event("collision_risk", rider_id)
    expected_ids = {
        http_event["metadata"]["event_id"],
        mqtt_event["metadata"]["event_id"],
    }

    ops_ws_task = asyncio.create_task(
        _wait_for_ws_events(_ws_url("/ws/events"), set(expected_ids), timeout_s=20.0)
    )
    rider_ws_task = asyncio.create_task(
        _wait_for_ws_events(
            _ws_url(f"/ws/rider/{rider_id}"),
            set(expected_ids),
            timeout_s=20.0,
            init_payload={
                "type": "location",
                "lat": 11.0168,
                "lng": 76.9558,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{API_BASE}/api/ai/event",
            headers={"x-api-key": API_KEY},
            json=http_event,
        )
        response.raise_for_status()

        duplicate_response = await client.post(
            f"{API_BASE}/api/ai/event",
            headers={"x-api-key": API_KEY},
            json=http_event,
        )
        duplicate_response.raise_for_status()

        recent_response = await client.get(
            f"{API_BASE}/api/ai/events/recent",
            params={"rider_id": rider_id, "limit": 20},
        )
        recent_response.raise_for_status()
        recent_payload = recent_response.json()
        if not isinstance(recent_payload, dict) or not isinstance(recent_payload.get("items"), list):
            raise AssertionError("/api/ai/events/recent returned unexpected payload")

    mqtt_publish.single(
        topic=MQTT_TOPIC,
        payload=json.dumps(mqtt_event),
        hostname=MQTT_HOST,
        port=MQTT_PORT,
        qos=1,
        retain=False,
    )

    ops_ws_messages = await ops_ws_task
    rider_ws_messages = await rider_ws_task
    if len(ops_ws_messages) < 2:
        raise AssertionError("Expected 2 AI_EVENT messages on /ws/events")
    if len(rider_ws_messages) < 2:
        raise AssertionError("Expected 2 AI_EVENT messages on /ws/rider/{rider_id}")

    await _assert_db_events(list(expected_ids))
    await _assert_single_record(http_event["metadata"]["event_id"])
    print("E2E PASS: HTTP+MQTT ingestion, DB persistence, duplicate guard, and rider websocket delivery verified")


if __name__ == "__main__":
    asyncio.run(main())