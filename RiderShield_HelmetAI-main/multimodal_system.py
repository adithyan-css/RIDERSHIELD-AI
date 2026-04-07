import argparse
import json
import time
from typing import Optional

import cv2

from multimodal.audio_analysis import AudioAnalysisEngine
from multimodal.context_engine import ContextEngine
from multimodal.event_database import EventDatabase
from multimodal.fusion_engine import EventDetectionFusionEngine
from multimodal.prompt_analyzer import PromptAnalyzer
from multimodal.query_engine import QueryExecutionEngine
from multimodal.video_analysis import VideoAnalysisEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multimodal Video Intelligence + Prompt Query Engine")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--video-fps", type=int, default=10)
    parser.add_argument("--db-path", type=str, default="multimodal_events.db")
    parser.add_argument("--no-ui", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    event_db = EventDatabase(db_path=args.db_path)
    prompt_analyzer = PromptAnalyzer()
    query_engine = QueryExecutionEngine(event_db=event_db, prompt_analyzer=prompt_analyzer)

    video = VideoAnalysisEngine(camera_index=args.camera_index, fps=args.video_fps)
    audio = AudioAnalysisEngine()
    context = ContextEngine(stop_speed_threshold=0.08)
    fusion = EventDetectionFusionEngine(min_persist_seconds=2.0)

    video.start()
    audio.start()

    last_audio = None
    window_name = "Multimodal Intelligence Engine"

    print("System started. Type queries in terminal, or press q in video window to stop.")
    print("Example query: Show risky driving moments confidence > 0.7")

    try:
        while True:
            snapshot = video.get_latest_snapshot(timeout=0.4)
            if snapshot is None:
                continue

            aud = audio.get_latest_signal(timeout=0.01)
            if aud is not None:
                last_audio = aud

            ctx = None
            if snapshot.frame is not None:
                ctx = context.update(snapshot.frame, snapshot.timestamp)

            events = fusion.evaluate(snapshot=snapshot, audio_signal=last_audio, context_signal=ctx)
            for event in events:
                event_db.add_event(event)
                print(
                    "EVENT",
                    event.event_type,
                    f"conf={event.confidence:.2f}",
                    f"start={event.start_time:.3f}",
                    f"end={event.end_time:.3f}",
                )

            if not args.no_ui and snapshot.frame is not None:
                frame = snapshot.frame.copy()
                txt = f"objs={len(snapshot.objects)} em={len(snapshot.emotions)} audio={last_audio.audio_event if last_audio else 'n/a'}"
                cv2.putText(frame, txt, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (235, 235, 235), 2, cv2.LINE_AA)
                cv2.putText(
                    frame,
                    "Terminal query mode: type and press Enter in terminal",
                    (15, 58),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (225, 225, 225),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow(window_name, frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break

            # Non-blocking terminal prompt every 2 seconds.
            if int(time.time() * 10) % 20 == 0:
                try:
                    import select
                    import sys

                    if select.select([sys.stdin], [], [], 0.0)[0]:
                        query = sys.stdin.readline().strip()
                        if query:
                            res = query_engine.execute_prompt(query)
                            print(json.dumps(res, indent=2))
                except Exception:
                    pass

    finally:
        video.stop()
        audio.stop()
        event_db.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
