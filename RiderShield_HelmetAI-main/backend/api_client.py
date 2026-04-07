import asyncio
import json
import os
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict
from urllib import error, request

import paho.mqtt.publish as mqtt_publish


class BackendAPIClient:
    """Reliable AI event client with HTTP persistence + MQTT streaming."""

    def __init__(
        self,
        backend_url: str | None = None,
        mqtt_host: str | None = None,
        mqtt_port: int | None = None,
        mqtt_topic: str | None = None,
        timeout_s: float = 5.0,
        max_attempts: int = 3,
        backoff_base_s: float = 0.5,
        failure_rate: float = 0.0,
    ) -> None:
        self.backend_url = (backend_url or os.getenv("RIDERSHIELD_API_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.ai_event_endpoint = f"{self.backend_url}/api/ai/event"

        self.mqtt_host = mqtt_host or os.getenv("RIDERSHIELD_MQTT_HOST") or "127.0.0.1"
        self.mqtt_port = int(mqtt_port or os.getenv("RIDERSHIELD_MQTT_PORT") or 1883)
        self.mqtt_topic = mqtt_topic or os.getenv("RIDERSHIELD_MQTT_TOPIC") or "rider/events"

        self.timeout_s = timeout_s
        self.max_attempts = max(1, max_attempts)
        self.backoff_base_s = max(0.1, backoff_base_s)
        self.failure_rate = max(0.0, min(1.0, failure_rate))

    def send_event_to_company(self, event: Dict[str, Any]) -> bool:
        payload = self._to_unified_event(event, channel="company")
        return self._send_with_retry(payload)

    def send_event_to_rider(self, event: Dict[str, Any]) -> bool:
        payload = self._to_unified_event(event, channel="rider")
        return self._send_with_retry(payload)

    async def async_send_event_to_company(self, event: Dict[str, Any]) -> bool:
        payload = self._to_unified_event(event, channel="company")
        return await self._send_with_retry_async(payload)

    async def async_send_event_to_rider(self, event: Dict[str, Any]) -> bool:
        payload = self._to_unified_event(event, channel="rider")
        return await self._send_with_retry_async(payload)

    def _send_with_retry(self, payload: Dict[str, Any]) -> bool:
        delay_s = self.backoff_base_s
        for attempt in range(1, self.max_attempts + 1):
            if self._simulate_failure():
                ok_http, ok_mqtt = False, False
            else:
                ok_http = self._post_event_http(payload)
                ok_mqtt = self._publish_event_mqtt(payload)

            if ok_http or ok_mqtt:
                return True

            if attempt < self.max_attempts:
                time.sleep(delay_s)
                delay_s *= 2

        return False

    async def _send_with_retry_async(self, payload: Dict[str, Any]) -> bool:
        delay_s = self.backoff_base_s
        for attempt in range(1, self.max_attempts + 1):
            if self._simulate_failure():
                ok_http, ok_mqtt = False, False
            else:
                ok_http, ok_mqtt = await asyncio.gather(
                    asyncio.to_thread(self._post_event_http, payload),
                    asyncio.to_thread(self._publish_event_mqtt, payload),
                )

            if ok_http or ok_mqtt:
                return True

            if attempt < self.max_attempts:
                await asyncio.sleep(delay_s)
                delay_s *= 2

        return False

    def _post_event_http(self, payload: Dict[str, Any]) -> bool:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.ai_event_endpoint,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with request.urlopen(req, timeout=self.timeout_s) as resp:
                return 200 <= int(resp.getcode()) < 300
        except error.HTTPError as exc:
            print(f"HTTP send failed status={exc.code}")
            return False
        except Exception as exc:
            print(f"HTTP send failed error={exc}")
            return False

    def _publish_event_mqtt(self, payload: Dict[str, Any]) -> bool:
        try:
            mqtt_publish.single(
                topic=self.mqtt_topic,
                payload=json.dumps(payload, separators=(",", ":")),
                hostname=self.mqtt_host,
                port=self.mqtt_port,
                qos=1,
                retain=False,
            )
            return True
        except Exception as exc:
            print(f"MQTT publish failed error={exc}")
            return False

    def _simulate_failure(self) -> bool:
        return self.failure_rate > 0 and random.random() < self.failure_rate

    @staticmethod
    def _to_unified_event(event: Dict[str, Any], channel: str) -> Dict[str, Any]:
        gps = event.get("gps") or event.get("location") or {}
        lat = float(gps.get("lat", 0.0))
        lng = float(gps.get("lng", gps.get("lon", 0.0)))

        timestamp = event.get("timestamp")
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        metadata = {
            "channel": channel,
            "event_id": event.get("event_id"),
            "digipin": event.get("digipin"),
            "video_path": event.get("video_path"),
            "signals": event.get("signals", {}),
            "source": event.get("source", "helmet_ai"),
        }

        for key, value in (event.get("metadata") or {}).items():
            metadata[key] = value

        return {
            "rider_id": str(event.get("rider_id", "unknown_rider")),
            "timestamp": str(timestamp),
            "location": {"lat": lat, "lng": lng},
            "event_type": str(event.get("event_type", "unknown")).lower(),
            "confidence": float(event.get("confidence", 0.0)),
            "metadata": metadata,
        }
