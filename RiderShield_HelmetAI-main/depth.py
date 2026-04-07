from typing import Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from pathlib import Path


def _ensure_torch_hub_trust(entries) -> None:
    hub_dir = Path(torch.hub.get_dir())
    hub_dir.mkdir(parents=True, exist_ok=True)
    trust_file = hub_dir / "trusted_list"
    trust_file.touch(exist_ok=True)

    current = {line.strip() for line in trust_file.read_text().splitlines() if line.strip()}
    missing = [entry for entry in entries if entry not in current]
    if not missing:
        return

    with trust_file.open("a", encoding="utf-8") as f:
        for entry in missing:
            f.write(f"{entry}\n")


class MiDaSDepthEstimator:
    """Depth estimator based on MiDaS_small for CPU-friendly relative depth."""

    def __init__(self, device: Optional[str] = None) -> None:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        _ensure_torch_hub_trust(
            [
                "intel-isl_MiDaS",
                "rwightman_gen-efficientnet-pytorch",
                "rwightman_pytorch-image-models",
            ]
        )

        self.model = torch.hub.load(
            "intel-isl/MiDaS",
            "MiDaS_small",
            trust_repo=True,
        )
        self.model.to(self.device)
        self.model.eval()

        transforms = torch.hub.load(
            "intel-isl/MiDaS",
            "transforms",
            trust_repo=True,
        )
        self.transform = transforms.small_transform

    def estimate_depth(self, frame_bgr: np.ndarray) -> np.ndarray:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        input_batch = self.transform(frame_rgb).to(self.device)

        with torch.no_grad():
            prediction = self.model(input_batch)
            prediction = F.interpolate(
                prediction.unsqueeze(1),
                size=frame_rgb.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze(1)

        depth_map = prediction[0].detach().cpu().numpy().astype(np.float32)
        return depth_map


def to_relative_distance_map(depth_map: np.ndarray) -> np.ndarray:
    """
    Convert MiDaS inverse-depth-like output into a stable relative distance map.
    Lower values indicate closer objects, higher values indicate farther objects.
    """
    if depth_map.size == 0:
        return depth_map

    p_low, p_high = np.percentile(depth_map, [5, 95])
    clipped = np.clip(depth_map, p_low, p_high)

    # MiDaS_small output tends to be higher for closer objects.
    closeness = (clipped - p_low) / (p_high - p_low + 1e-6)
    distance_map = 1.05 - closeness
    return distance_map.astype(np.float32)


def extract_object_distance(distance_map: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[float]:
    h, w = distance_map.shape[:2]
    x1, y1, x2, y2 = bbox

    x1 = max(0, min(x1, w - 1))
    x2 = max(0, min(x2, w - 1))
    y1 = max(0, min(y1, h - 1))
    y2 = max(0, min(y2, h - 1))

    if x2 <= x1 or y2 <= y1:
        return None

    roi = distance_map[y1:y2, x1:x2]
    if roi.size == 0:
        return None

    return float(np.median(roi))
