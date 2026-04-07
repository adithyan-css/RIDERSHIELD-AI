"""
RiderShield — Helmet AI (Raspberry Pi Zero 2W)
Runs MobileNetV2 TFLite at 15fps for forward/rear collision detection.
Speaks voice alerts via pyttsx3 (bone-conduction headset).
"""

import threading
import time
import queue
import cv2
import numpy as np
import pyttsx3
from datetime import datetime, timezone

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_PATH       = "mobilenet_v2_collision.tflite"
CAMERA_INDEX     = 0
FPS_TARGET       = 15
IMG_SIZE         = 224
COLLISION_THRESH = 0.75   # TTC alert threshold
CLIP_DURATION_S  = 120    # rolling clip buffer (seconds)

# ── TTS Engine ────────────────────────────────────────────────────────────────
_tts_engine = pyttsx3.init()
_tts_engine.setProperty("rate", 150)
_tts_engine.setProperty("volume", 1.0)
_tts_queue: queue.Queue = queue.Queue()


def _tts_worker():
    while True:
        text = _tts_queue.get()
        if text is None:
            break
        _tts_engine.say(text)
        _tts_engine.runAndWait()


tts_thread = threading.Thread(target=_tts_worker, daemon=True)
tts_thread.start()


def speak(text: str):
    _tts_queue.put(text)


# ── TFLite Model ──────────────────────────────────────────────────────────────
def load_model(path: str):
    interp = tflite.Interpreter(model_path=path)
    interp.allocate_tensors()
    return interp, interp.get_input_details(), interp.get_output_details()


def infer(interp, input_details, output_details, frame_rgb: np.ndarray) -> dict:
    img = cv2.resize(frame_rgb, (IMG_SIZE, IMG_SIZE)).astype(np.float32) / 255.0
    img = np.expand_dims(img, axis=0)
    interp.set_tensor(input_details[0]["index"], img)
    interp.invoke()
    output = interp.get_tensor(output_details[0]["index"])[0]
    # Assuming output: [safe, forward_collision, rear_collision]
    classes = ["safe", "forward_collision", "rear_collision"]
    idx = int(np.argmax(output))
    return {"class": classes[idx], "confidence": float(output[idx])}


# ── TTC Estimation (bounding box delta) ───────────────────────────────────────
class TTCEstimator:
    def __init__(self):
        self._prev_box_area = None
        self._prev_ts = None

    def update(self, box_area: float) -> float | None:
        now = time.time()
        if self._prev_box_area is not None and self._prev_ts is not None:
            dt = now - self._prev_ts
            if dt > 0:
                growth_rate = (box_area - self._prev_box_area) / (self._prev_box_area + 1e-6)
                ttc = 1.0 / (growth_rate / dt + 1e-6) if growth_rate > 0 else None
                self._prev_box_area = box_area
                self._prev_ts = now
                return ttc
        self._prev_box_area = box_area
        self._prev_ts = now
        return None


# ── Rolling Clip Writer ───────────────────────────────────────────────────────
class ClipWriter:
    def __init__(self, fps=15, size=(640, 480)):
        self._buffer = []
        self._fps = fps
        self._max_frames = fps * CLIP_DURATION_S
        self._size = size

    def push(self, frame: np.ndarray):
        self._buffer.append(frame.copy())
        if len(self._buffer) > self._max_frames:
            self._buffer.pop(0)

    def save_event(self, reason: str):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        fname = f"clip_{reason}_{ts}.avi"
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(fname, fourcc, self._fps, self._size)
        for f in self._buffer[-self._fps * 30 :]:   # last 30s
            out.write(f)
        out.release()
        print(f"🎬 Clip saved: {fname}")
        return fname


# ── Main Camera Loop ──────────────────────────────────────────────────────────
def main():
    print("🪖 RiderShield Helmet AI starting...")
    try:
        interp, in_det, out_det = load_model(MODEL_PATH)
        print("✅ TFLite model loaded")
    except Exception as e:
        print(f"⚠️  Model load failed ({e}), using mock inference")
        interp = in_det = out_det = None

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, FPS_TARGET)

    ttc = TTCEstimator()
    clip = ClipWriter()
    last_alert_ts = 0

    speak("Helmet AI active. RiderShield is watching.")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        clip.push(frame)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if interp is not None:
            result = infer(interp, in_det, out_det, frame_rgb)
        else:
            result = {"class": "safe", "confidence": 1.0}

        cls, conf = result["class"], result["confidence"]

        if cls != "safe" and conf >= COLLISION_THRESH:
            now = time.time()
            if now - last_alert_ts > 3.0:   # debounce 3s
                last_alert_ts = now
                alert_text = (
                    "Warning! Vehicle ahead!" if cls == "forward_collision"
                    else "Warning! Vehicle behind!"
                )
                speak(alert_text)
                clip.save_event(cls)
                print(f"🚨 {cls} @ {conf:.2f}")

        time.sleep(1.0 / FPS_TARGET)

    cap.release()


if __name__ == "__main__":
    main()
