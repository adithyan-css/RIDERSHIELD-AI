import asyncio
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from urllib import error, request

import paho.mqtt.publish as mqtt_publish


logger = logging.getLogger(__name__)


class BackendAPIClient:
    """Reliable AI event client with HTTP persistence + MQTT streaming."""

    def __init__(
        self,
        backend_url: str | None = None,
        api_key: str | None = None,
        mqtt_host: str | None = None,
        mqtt_port: int | None = None,
        mqtt_topic: str | None = None,
        timeout_s: float = 5.0,
        max_attempts: int = 3,
        backoff_base_s: float = 0.5,
        failure_rate: float = 0.0,
    ) -> None:
        self.backend_url = (backend_url or os.getenv("RIDERSHIELD_API_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("RIDERSHIELD_API_KEY") or ""

        self.mqtt_host = mqtt_host or os.getenv("RIDERSHIELD_MQTT_HOST") or ""
        self.mqtt_port = int(mqtt_port or os.getenv("RIDERSHIELD_MQTT_PORT") or 1883)
        self.mqtt_topic = mqtt_topic or os.getenv("RIDERSHIELD_MQTT_TOPIC") or ""

        self._validate_required_config()

        self.ai_event_endpoint = f"{self.backend_url}/api/ai/event"

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
        event_id = str((payload.get("metadata") or {}).get("event_id", "unknown"))
        for attempt in range(1, self.max_attempts + 1):
            logger.info("ai_send_attempt event_id=%s attempt=%s", event_id, attempt)
            if self._simulate_failure():
                ok = False
            else:
                ok = self._send_once(payload)

            if ok:
                logger.info("ai_send_success event_id=%s attempt=%s", event_id, attempt)
                return True

            logger.warning("ai_send_retry event_id=%s attempt=%s", event_id, attempt)

            if attempt < self.max_attempts:
                time.sleep(delay_s)
                delay_s *= 2

        logger.error("ai_send_failed event_id=%s attempts=%s", event_id, self.max_attempts)
        return False

    async def _send_with_retry_async(self, payload: Dict[str, Any]) -> bool:
        delay_s = self.backoff_base_s
        event_id = str((payload.get("metadata") or {}).get("event_id", "unknown"))
        for attempt in range(1, self.max_attempts + 1):
            logger.info("ai_send_attempt_async event_id=%s attempt=%s", event_id, attempt)
            if self._simulate_failure():
                ok = False
            else:
                ok = await asyncio.to_thread(self._send_once, payload)

            if ok:
                logger.info("ai_send_success_async event_id=%s attempt=%s", event_id, attempt)
                return True

            logger.warning("ai_send_retry_async event_id=%s attempt=%s", event_id, attempt)

            if attempt < self.max_attempts:
                await asyncio.sleep(delay_s)
                delay_s *= 2

        logger.error("ai_send_failed_async event_id=%s attempts=%s", event_id, self.max_attempts)
        return False

    def _send_once(self, payload: Dict[str, Any]) -> bool:
        # Transport strategy: HTTP first, MQTT fallback. Never emit on both channels.
        if self._post_event_http(payload):
            return True
        return self._publish_event_mqtt(payload)

    def _post_event_http(self, payload: Dict[str, Any]) -> bool:
        event_id = str((payload.get("metadata") or {}).get("event_id", "unknown"))
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.ai_event_endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout_s) as resp:
                return 200 <= int(resp.getcode()) < 300
        except error.HTTPError as exc:
            logger.warning("ai_http_failed event_id=%s status=%s", event_id, exc.code)
            return False
        except Exception as exc:
            logger.exception("ai_http_failed event_id=%s error=%s", event_id, exc)
            return False

    def _publish_event_mqtt(self, payload: Dict[str, Any]) -> bool:
        event_id = str((payload.get("metadata") or {}).get("event_id", "unknown"))
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
            logger.exception("ai_mqtt_failed event_id=%s error=%s", event_id, exc)
            return False

    def _simulate_failure(self) -> bool:
        return self.failure_rate > 0 and random.random() < self.failure_rate

    def _validate_required_config(self) -> None:
        required = {
            "RIDERSHIELD_API_URL": self.backend_url,
            "RIDERSHIELD_API_KEY": self.api_key,
            "RIDERSHIELD_MQTT_HOST": self.mqtt_host,
            "RIDERSHIELD_MQTT_TOPIC": self.mqtt_topic,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Missing required RiderShield configuration: {joined}")

    @staticmethod
    def _to_iso_timestamp(raw_timestamp: Any) -> str:
        if isinstance(raw_timestamp, datetime):
            ts = raw_timestamp
        elif isinstance(raw_timestamp, (int, float)):
            ts = datetime.fromtimestamp(float(raw_timestamp), tz=timezone.utc)
        elif isinstance(raw_timestamp, str) and raw_timestamp.strip():
            text = raw_timestamp.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                ts = datetime.fromisoformat(text)
            except ValueError:
                ts = datetime.now(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        return ts.isoformat()

    @staticmethod
    def _to_unified_event(event: Dict[str, Any], channel: str) -> Dict[str, Any]:
        gps = event.get("gps") or event.get("location") or {}
        lat = float(gps.get("lat", 0.0))
        lng = float(gps.get("lng", gps.get("lon", 0.0)))

        timestamp = event.get("timestamp")
        timestamp_iso = BackendAPIClient._to_iso_timestamp(timestamp)

        metadata_input = event.get("metadata") or {}
        generated_event_id = (
            str(event.get("event_id") or metadata_input.get("event_id") or "").strip() or str(uuid.uuid4())
        )

        metadata = {
            "channel": channel,
            "event_id": generated_event_id,
            "digipin": event.get("digipin"),
            "video_path": event.get("video_path"),
            "signals": event.get("signals", {}),
            "source": event.get("source", "helmet_ai"),
        }

        for key, value in metadata_input.items():
            metadata[key] = value

        metadata["event_id"] = generated_event_id

        return {
            "rider_id": str(event.get("rider_id", "unknown_rider")),
            "timestamp": timestamp_iso,
            "location": {"lat": lat, "lng": lng},
            "event_type": str(event.get("event_type", "unknown")).lower(),
            "confidence": float(event.get("confidence", 0.0)),
            "metadata": metadata,
        }
