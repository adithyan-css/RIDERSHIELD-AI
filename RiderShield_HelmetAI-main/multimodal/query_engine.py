from datetime import datetime
from typing import Dict, List

from multimodal.event_database import EventDatabase
from multimodal.models import ParsedIntent
from multimodal.prompt_analyzer import PromptAnalyzer


class QueryExecutionEngine:
    """Parses prompt, executes indexed query, and returns operator-friendly results."""

    def __init__(self, event_db: EventDatabase, prompt_analyzer: PromptAnalyzer) -> None:
        self.event_db = event_db
        self.prompt_analyzer = prompt_analyzer

    def execute_prompt(self, prompt: str) -> Dict:
        parsed: ParsedIntent = self.prompt_analyzer.parse(prompt)
        if parsed.ambiguous or not parsed.intent:
            return {
                "ok": False,
                "reason": parsed.reason,
                "results": [],
            }

        rows = self.event_db.query_events(
            event_type=parsed.intent,
            min_confidence=parsed.min_confidence,
            since_seconds=parsed.time_range_seconds,
            limit=100,
        )

        results: List[Dict] = []
        for r in rows:
            ts = datetime.utcfromtimestamp(r["start_time"]).strftime("%Y-%m-%d %H:%M:%S UTC")
            results.append(
                {
                    "timestamp": ts,
                    "event_type": r["event_type"],
                    "confidence": round(float(r["confidence"]), 3),
                    "short_description": r["description"],
                    "supporting_signals": r["signals_json"],
                }
            )

        return {
            "ok": True,
            "intent": parsed.intent,
            "count": len(results),
            "results": results,
        }
