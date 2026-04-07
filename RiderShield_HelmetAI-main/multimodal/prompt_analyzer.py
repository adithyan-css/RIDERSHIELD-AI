import re
from typing import Dict, List, Optional

from multimodal.models import ParsedIntent


class PromptAnalyzer:
    """Converts natural language operator queries into structured event intents."""

    EVENT_MAP: Dict[str, List[str]] = {
        "distress_event": [
            "crying",
            "cried",
            "distress",
            "fear",
            "sad",
            "person crying",
            "rider crying",
        ],
        "possible_petrol_stop": [
            "petrol bunk",
            "fuel stop",
            "gas station",
            "petrol stop",
        ],
        "suspicious_interaction": [
            "unknown person",
            "suspicious",
            "interaction",
            "stranger",
            "fight",
            "aggressive interaction",
        ],
        "collision_risk": [
            "risky driving",
            "risky moment",
            "collision",
            "near crash",
            "dangerous driving",
            "ttc",
        ],
        "long_stop": [
            "stopped for more than",
            "stopped",
            "halt",
            "idle",
            "standstill",
        ],
    }

    def parse(self, query: str) -> ParsedIntent:
        text = self._normalize(query)
        matched_intents = []
        for intent, keywords in self.EVENT_MAP.items():
            if any(k in text for k in keywords):
                matched_intents.append(intent)

        min_conf = self._extract_confidence(text)
        time_range = self._extract_time_range_seconds(text)

        if len(matched_intents) == 1:
            return ParsedIntent(
                intent=matched_intents[0],
                min_confidence=min_conf,
                time_range_seconds=time_range,
                raw_query=query,
            )

        if len(matched_intents) > 1:
            return ParsedIntent(
                intent=None,
                ambiguous=True,
                reason=f"Ambiguous query matches multiple intents: {matched_intents}",
                raw_query=query,
            )

        return ParsedIntent(
            intent=None,
            ambiguous=True,
            reason="No supported intent detected. Try asking for distress, collision risk, suspicious interaction, petrol stop, or long stop.",
            raw_query=query,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _extract_confidence(text: str) -> float:
        m = re.search(r"confidence\s*(?:>|>=|above)?\s*(0\.\d+|1\.0|1)", text)
        if not m:
            return 0.7
        return max(0.0, min(1.0, float(m.group(1))))

    @staticmethod
    def _extract_time_range_seconds(text: str) -> Optional[int]:
        m_min = re.search(r"last\s+(\d+)\s+min", text)
        if m_min:
            return int(m_min.group(1)) * 60

        m_hr = re.search(r"last\s+(\d+)\s+hour", text)
        if m_hr:
            return int(m_hr.group(1)) * 3600

        return None
