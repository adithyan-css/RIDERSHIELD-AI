import asyncio
import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.services.hazard_service import process_hfv

logger = logging.getLogger(__name__)


class MQTTIngestionClient:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="ridershield-backend",
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._started = False

    def start(self) -> None:
        if self._started:
            return

        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        try:
            self._client.connect_async(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_PORT,
                settings.MQTT_KEEPALIVE,
            )
            self._client.loop_start()
            self._started = True
            logger.info(
                "MQTT client started at %s:%s",
                settings.MQTT_BROKER_HOST,
                settings.MQTT_PORT,
            )
        except Exception:
            logger.exception("MQTT client failed to start")

    def stop(self) -> None:
        if not self._started:
            return
        self._client.loop_stop()
        self._client.disconnect()
        self._started = False
        logger.info("MQTT client stopped")

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        reason_code: Any,
        properties: Any = None,
    ) -> None:
        if isinstance(reason_code, (int, float)):
            code = int(reason_code)
        else:
            code = int(getattr(reason_code, "value", -1))
        if code != 0:
            logger.error("MQTT connection failed with reason code=%s", code)
            return

        client.subscribe(settings.MQTT_TOPIC_HFV)
        logger.info("Subscribed to topic %s", settings.MQTT_TOPIC_HFV)

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if not isinstance(payload, dict):
                logger.warning("MQTT payload ignored; expected JSON object")
                return
        except Exception:
            logger.exception("Failed to decode MQTT payload")
            return

        future = asyncio.run_coroutine_threadsafe(
            process_hfv(payload, source="mqtt"),
            self._loop,
        )
        future.add_done_callback(self._log_result)

    @staticmethod
    def _log_result(future: asyncio.Future[Any]) -> None:
        try:
            result = future.result()
            logger.debug("MQTT HFV processed id=%s", result.get("id"))
        except Exception:
            logger.exception("MQTT HFV processing failed")


_mqtt_client: MQTTIngestionClient | None = None


def start_mqtt_client(loop: asyncio.AbstractEventLoop) -> None:
    global _mqtt_client
    if _mqtt_client is not None:
        return

    _mqtt_client = MQTTIngestionClient(loop)
    _mqtt_client.start()


def stop_mqtt_client() -> None:
    global _mqtt_client
    if _mqtt_client is not None:
        _mqtt_client.stop()
        _mqtt_client = None