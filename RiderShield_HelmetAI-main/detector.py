from typing import Dict, List

from ultralytics import YOLO


class VehicleDetector:
    """YOLOv8 wrapper for filtering road-user classes relevant to awareness."""

    TARGET_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle", "person"}

    def __init__(self, model_name: str = "yolov8n.pt", conf_threshold: float = 0.35) -> None:
        self.model = YOLO(model_name)
        self.conf_threshold = conf_threshold

    def detect(self, frame) -> List[Dict]:
        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            verbose=False,
            imgsz=640,
            device="cpu",
        )

        detections: List[Dict] = []
        if not results:
            return detections

        result = results[0]
        boxes = result.boxes
        names = result.names

        if boxes is None:
            return detections

        for box in boxes:
            cls_id = int(box.cls.item())
            class_name = names.get(cls_id, str(cls_id))
            if class_name not in self.TARGET_CLASSES:
                continue

            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf.item())
            cx = int((x1 + x2) * 0.5)
            cy = int((y1 + y2) * 0.5)

            detections.append(
                {
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2),
                    "centroid": (cx, cy),
                }
            )

        return detections
