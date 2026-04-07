import logging
from typing import Dict

from backend.api_client import BackendAPIClient
from backend.retry_manager import RetryManager


logger = logging.getLogger(__name__)


class SOSManager:
    """Dispatches incident events reliably to company and rider channels."""

    def __init__(self, api_client: BackendAPIClient, retry_manager: RetryManager) -> None:
        self.api_client = api_client
        self.retry_manager = retry_manager

        def sender(event: Dict) -> bool:
            return self.api_client.send_event_to_company(self._with_channels(event))

        self.retry_manager.start(sender)

    @staticmethod
    def _with_channels(event: Dict) -> Dict:
        outgoing = dict(event)
        metadata = dict(outgoing.get("metadata", {}))
        metadata["channels"] = ["company", "rider"]
        outgoing["metadata"] = metadata
        return outgoing

    def handle_incident_event(self, event: Dict) -> None:
        outbound = self._with_channels(event)
        ok = self.api_client.send_event_to_company(outbound)
        event_id = str((outbound.get("metadata") or {}).get("event_id") or outbound.get("event_id") or "unknown")

        if ok:
            logger.info("sos_send_success event_id=%s", event_id)
            return

        logger.warning("sos_send_failed_enqueued event_id=%s", event_id)
        self.retry_manager.enqueue(outbound)

    def shutdown(self) -> None:
        self.retry_manager.stop()
