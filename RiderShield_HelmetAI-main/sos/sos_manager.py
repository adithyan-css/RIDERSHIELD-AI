from typing import Dict

from backend.api_client import BackendAPIClient
from backend.retry_manager import RetryManager


class SOSManager:
    """Dispatches incident events reliably to company and rider channels."""

    def __init__(self, api_client: BackendAPIClient, retry_manager: RetryManager) -> None:
        self.api_client = api_client
        self.retry_manager = retry_manager

        def sender(event: Dict) -> bool:
            ok_company = self.api_client.send_event_to_company(event)
            ok_rider = self.api_client.send_event_to_rider(event)
            return ok_company and ok_rider

        self.retry_manager.start(sender)

    def handle_incident_event(self, event: Dict) -> None:
        ok_company = self.api_client.send_event_to_company(event)
        ok_rider = self.api_client.send_event_to_rider(event)

        if ok_company and ok_rider:
            print("Event sent successfully to company+rider")
            return

        print("Event send failed, enqueued for retry")
        self.retry_manager.enqueue(event)

    def shutdown(self) -> None:
        self.retry_manager.stop()
