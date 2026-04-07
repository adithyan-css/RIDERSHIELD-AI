from typing import Dict, List

import cv2
import numpy as np


SAFE_COLOR = (30, 210, 30)
APPROACHING_COLOR = (0, 220, 255)
COLLISION_COLOR = (0, 0, 255)
FORWARD_COLOR = (0, 200, 0)
REAR_COLOR = (0, 0, 200)
TEXT_COLOR = (245, 245, 245)


def zone_for_centroid(x: int, frame_width: int) -> str:
    return "REAR" if x < frame_width // 2 else "FORWARD"


def draw_zones(frame: np.ndarray) -> None:
    h, w = frame.shape[:2]
    mid_x = w // 2

    cv2.line(frame, (mid_x, 0), (mid_x, h), (255, 255, 255), 2)

    cv2.putText(
        frame,
        "REAR ZONE",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        REAR_COLOR,
        2,
        cv2.LINE_AA,
    )

    text_size, _ = cv2.getTextSize("FORWARD ZONE", cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)
    cv2.putText(
        frame,
        "FORWARD ZONE",
        (w - text_size[0] - 20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        FORWARD_COLOR,
        2,
        cv2.LINE_AA,
    )


def draw_lane_roi(frame: np.ndarray, lane_ratio: float) -> None:
    lane_ratio = max(0.05, min(1.0, lane_ratio))
    h, w = frame.shape[:2]
    half = w / 2.0
    keep_half = (half * lane_ratio) / 2.0

    rear_center = int(w * 0.25)
    forward_center = int(w * 0.75)

    rear_x1 = int(rear_center - keep_half)
    rear_x2 = int(rear_center + keep_half)
    fwd_x1 = int(forward_center - keep_half)
    fwd_x2 = int(forward_center + keep_half)

    cv2.rectangle(frame, (rear_x1, 55), (rear_x2, h - 20), (120, 120, 255), 1)
    cv2.rectangle(frame, (fwd_x1, 55), (fwd_x2, h - 20), (120, 255, 120), 1)

    cv2.putText(
        frame,
        f"Lane ROI: {lane_ratio:.2f}",
        (15, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )


def _format_ttc(ttc: float) -> str:
    return f"{ttc:.2f}s"


def draw_tracks(frame: np.ndarray, tracks: List[Dict]) -> str:
    max_alert = "SAFE"

    for track in tracks:
        x1, y1, x2, y2 = track["bbox"]
        zone = track["zone"]
        alert_level = track.get("alert_level", "SAFE")
        if alert_level == "COLLISION":
            color = COLLISION_COLOR
            max_alert = "COLLISION"
        elif alert_level == "APPROACHING":
            color = APPROACHING_COLOR
            if max_alert != "COLLISION":
                max_alert = "APPROACHING"
        else:
            color = SAFE_COLOR
            # Keep subtle zone identity for safe state.
            color = REAR_COLOR if zone == "REAR" else FORWARD_COLOR

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        label = f"ID {track['id']} | {track['class_name']}"
        if track.get("smoothed_distance") is not None:
            label += f" | D:{track['smoothed_distance']:.2f}"
        label += f" | V:{track.get('closing_speed', 0.0):.2f}"
        if track.get("ttc") is not None:
            label += f" | TTC:{_format_ttc(track['ttc'])}"
        label += f" | R:{track.get('risk_score', 0.0):.2f}"

        y_text = max(20, y1 - 8)
        cv2.putText(
            frame,
            label,
            (x1, y_text),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
            cv2.LINE_AA,
        )

    return max_alert


def draw_fps(frame: np.ndarray, fps: float) -> None:
    cv2.putText(
        frame,
        f"FPS: {fps:.1f}",
        (15, frame.shape[0] - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )


def draw_collision_warning(frame: np.ndarray, message: str = "COLLISION WARNING") -> None:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 50), (w, 105), (0, 0, 180), -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    text = f"WARNING: {message}"
    text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    x = (w - text_size[0]) // 2
    cv2.putText(
        frame,
        text,
        (x, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
