import os
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Callable, List

import numpy as np

from backend.api_client import BackendAPIClient
from backend.retry_manager import RetryManager
from dashcam.event_detector import MultiSignalFusionDetector
from dashcam.state_machine import IncidentStateMachine
from integration.app_interface import AppInterface
from main import parse_args
from multimodal.event_database import EventDatabase
from multimodal.fusion_engine import EventDetectionFusionEngine
from multimodal.models import AudioSignal, ContextSignal, DetectedObject, EmotionSignal, FusedEvent, VideoSnapshot
from multimodal.prompt_analyzer import PromptAnalyzer
from multimodal.query_engine import QueryExecutionEngine
from navigation.navigation_manager import NavigationManager
from navigation.route_loader import load_default_marina_route
from sos.event_builder import build_incident_event
from sos.metadata import MetadataProvider
from sos.sos_manager import SOSManager
from tracker import SimpleCentroidTracker
from vision.collision_logic import CollisionAlertManager


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    duration_ms: float


def _run_compile_check() -> None:
    cmd = [
        sys.executable,
        "-m",
        "py_compile",
    ]

    py_files = []
    for root, _, files in os.walk("."):
        if root.startswith("./venv"):
            continue
        for file_name in files:
            if file_name.endswith(".py"):
                py_files.append(os.path.join(root, file_name))

    proc = subprocess.run(cmd + py_files, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"py_compile failed: {proc.stderr.strip() or proc.stdout.strip()}")


def _test_app_state_gating() -> None:
    app = AppInterface()
    st = app.get_rider_state()
    assert not st.is_logged_in and not st.is_on_delivery

    app.simulate_login()
    app.simulate_delivery_start()
    st = app.get_rider_state()
    assert st.is_logged_in and st.is_on_delivery

    app.simulate_delivery_stop()
    st = app.get_rider_state()
    assert st.is_logged_in and not st.is_on_delivery


def _test_navigation_progression() -> None:
    route = load_default_marina_route()
    nav = NavigationManager(route, step_interval_seconds=0.01)
    start_text = nav.start(now=0.0)
    assert "Marina Beach" in start_text

    s0 = nav.tick(0.0)
    assert s0 is not None
    s1 = nav.tick(0.02)
    assert s1 is not None


def _test_tracker_ttc_alert_path() -> None:
    tracker = SimpleCentroidTracker(confirmation_frames=2)
    now = 0.0
    tracks = []

    for d in [0.95, 0.78, 0.62, 0.50, 0.38]:
        now += 0.12
        det = [
            {
                "class_id": 2,
                "class_name": "car",
                "confidence": 0.95,
                "bbox": (120, 100, 280, 300),
                "centroid": (200, 200),
                "zone": "FORWARD",
                "distance": d,
                "frame_width": 960,
            }
        ]
        tracks = tracker.update(det, now)

    assert tracks
    assert tracks[0].get("alert_level") in ("SAFE", "APPROACHING", "COLLISION")


def _test_collision_logic_directional_events() -> None:
    cam = CollisionAlertManager()

    forward_collision = [
        {
            "id": 10,
            "alert_level": "COLLISION",
            "zone": "FORWARD",
            "ttc": 1.1,
            "smoothed_distance": 0.45,
            "risk_score": 2.3,
        }
    ]
    rear_approach = [
        {
            "id": 11,
            "alert_level": "APPROACHING",
            "zone": "REAR",
            "ttc": 3.0,
            "smoothed_distance": 0.55,
            "risk_score": 1.2,
        }
    ]

    ev1 = cam.evaluate(forward_collision, now=10.0)
    assert ev1 is not None
    assert ev1["kind"] == "collision"
    assert "ahead" in ev1["text"]
    assert ev1["source"] == "vision_live"

    ev2 = cam.evaluate(rear_approach, now=20.0)
    assert ev2 is not None
    assert ev2["kind"] == "warning"
    assert "rear" in ev2["text"]
    assert ev2["source"] == "vision_live"


def _test_fusion_state_machine_confirmation() -> None:
    fusion = MultiSignalFusionDetector(window_size=8, persistent_frames=3)
    sm = IncidentStateMachine(suspicious_frames_required=3, confirmation_threshold=0.55, recovery_seconds=1.0)

    frame = np.zeros((540, 960, 3), dtype=np.uint8)
    tracks = [{"id": 1, "bbox": (100, 100, 220, 260), "ttc": 1.0, "alert_level": "COLLISION", "zone": "FORWARD"}]

    fusion.inject_simulated_accident()
    confirmed = False
    for _ in range(12):
        out = fusion.update(frame, tracks)
        state = sm.update(out["suspicious"], out["confidence"], time.time())
        if state.confirmed:
            confirmed = True
            break

    assert confirmed


def _test_event_builder_and_metadata() -> None:
    metadata = MetadataProvider().build_metadata()
    event = build_incident_event(
        rider_id="rider_001",
        metadata=metadata,
        video_path="incident_clips/sample.mp4",
        confidence=0.91,
        signals={"vision": {"score": 0.7}, "motion": {"score": 0.8}, "ttc": {"score": 0.6}},
    )

    assert event["event_type"] == "ACCIDENT"
    assert "digipin" in event
    assert "gps" in event
    assert event["source"] == "helmet_dashcam"


def _test_retry_fallback_reliability() -> None:
    fallback_dir = "failed_events_ci"
    if os.path.isdir(fallback_dir):
        for fn in os.listdir(fallback_dir):
            os.remove(os.path.join(fallback_dir, fn))

    api = BackendAPIClient(failure_rate=1.0)
    retry = RetryManager(fallback_dir=fallback_dir, retry_interval=0.1)
    sos = SOSManager(api_client=api, retry_manager=retry)

    event = {
        "event_id": "ci-test-event",
        "event_type": "ACCIDENT",
        "timestamp": "2026-04-07T00:00:00Z",
        "gps": {"lat": 13.05, "lon": 80.28},
        "digipin": "DIGI-TEST",
        "video_path": "incident_clips/sample.mp4",
        "confidence": 0.9,
        "signals": {"vision": 0.9, "motion": 0.8, "ttc": 0.7},
        "source": "helmet_dashcam",
    }

    sos.handle_incident_event(event)
    time.sleep(0.9)
    sos.shutdown()

    expected = os.path.join(fallback_dir, "ci-test-event.json")
    assert os.path.exists(expected)

    os.remove(expected)
    try:
        os.rmdir(fallback_dir)
    except OSError:
        pass


def _test_main_cli_contract() -> None:
    _ = parse_args


def _test_multimodal_prompt_query_and_fusion() -> None:
    db = EventDatabase(":memory:")
    analyzer = PromptAnalyzer()
    query = QueryExecutionEngine(db, analyzer)
    fusion = EventDetectionFusionEngine(min_persist_seconds=0.0)

    intent = analyzer.parse("Show risky driving moments confidence > 0.7")
    assert intent.intent == "collision_risk"

    now = time.time()
    db.add_event(
        FusedEvent(
            event_type="collision_risk",
            start_time=now - 10,
            end_time=now - 9,
            confidence=0.90,
            contributing_signals={"ttc": {"min_ttc": 1.2}},
            description="CI multimodal event",
        )
    )

    out = query.execute_prompt("Show risky driving moments confidence > 0.7")
    assert out["ok"] and out["count"] >= 1

    snap = VideoSnapshot(
        timestamp=now,
        objects=[
            DetectedObject(
                object_id=1,
                class_name="person",
                bbox=(0, 0, 100, 120),
                timestamp=now,
                confidence=0.9,
            )
        ],
        emotions=[EmotionSignal(object_id=1, emotion="sad", confidence=0.8, timestamp=now)],
        traffic_count=0,
    )
    aud = AudioSignal(audio_event="crying", confidence=0.9, timestamp=now)
    ctx = ContextSignal(speed=0.01, is_stopped=True, stop_duration=80, timestamp=now, time_of_day="day")
    evts = fusion.evaluate(snap, aud, ctx)
    assert any(e.event_type == "distress_event" for e in evts)

    db.close()


def run_test(name: str, fn: Callable[[], None]) -> TestResult:
    start = time.perf_counter()
    try:
        fn()
        return TestResult(name=name, passed=True, details="ok", duration_ms=(time.perf_counter() - start) * 1000)
    except Exception as exc:  # noqa: BLE001
        details = f"{exc}\n{traceback.format_exc(limit=2)}"
        return TestResult(name=name, passed=False, details=details, duration_ms=(time.perf_counter() - start) * 1000)


def main() -> int:
    tests = [
        ("compile_check", _run_compile_check),
        ("app_state_gating", _test_app_state_gating),
        ("navigation_progression", _test_navigation_progression),
        ("tracker_ttc_alert_path", _test_tracker_ttc_alert_path),
        ("collision_logic_directional", _test_collision_logic_directional_events),
        ("fusion_state_machine_confirmation", _test_fusion_state_machine_confirmation),
        ("event_builder_metadata", _test_event_builder_and_metadata),
        ("retry_fallback_reliability", _test_retry_fallback_reliability),
        ("main_cli_contract", _test_main_cli_contract),
        ("multimodal_prompt_query_and_fusion", _test_multimodal_prompt_query_and_fusion),
    ]

    results: List[TestResult] = []
    print("=== SMART DASHCAM CI SMOKE ===")
    for name, fn in tests:
        result = run_test(name, fn)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {name} ({result.duration_ms:.1f} ms)")
        if not result.passed:
            print(result.details)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    print("=== SUMMARY ===")
    print(f"total={len(results)} passed={passed} failed={failed}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
