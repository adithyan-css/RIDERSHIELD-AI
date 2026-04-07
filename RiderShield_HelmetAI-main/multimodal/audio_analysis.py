import collections
import queue
import threading
import time
from typing import Deque, Dict, List, Optional

import numpy as np

from multimodal.models import AudioSignal


class AudioAnalysisEngine:
    """YAMNet-based audio event detection with rolling-window smoothing."""

    TARGET_LABEL_MAP = {
        "Crying, sobbing": "crying",
        "Scream": "scream",
        "Yell": "shouting",
        "Shout": "shouting",
        "Conversation": "argument_noise",
        "Silence": "silence",
    }

    def __init__(self, sample_rate: int = 16000, chunk_seconds: float = 0.96) -> None:
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.chunk_samples = int(sample_rate * chunk_seconds)

        self._queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=32)
        self._signal_queue: "queue.Queue[AudioSignal]" = queue.Queue(maxsize=32)
        self._stop_event = threading.Event()
        self._audio_thread: Optional[threading.Thread] = None
        self._infer_thread: Optional[threading.Thread] = None

        self._window: Deque[AudioSignal] = collections.deque(maxlen=6)

        self._yamnet = None
        self._class_names: List[str] = []
        self._sd = None
        self._load_models()

    def _load_models(self) -> None:
        try:
            import sounddevice as sd  # type: ignore
            import tensorflow as tf  # type: ignore
            import tensorflow_hub as hub  # type: ignore

            self._sd = sd
            self._yamnet = hub.load("https://tfhub.dev/google/yamnet/1")

            class_map_path = tf.keras.utils.get_file(
                "yamnet_class_map.csv",
                "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv",
            )
            with open(class_map_path, "r", encoding="utf-8") as f:
                rows = f.read().splitlines()[1:]
                self._class_names = [line.split(",")[2] for line in rows]
        except Exception:
            self._yamnet = None
            self._sd = None
            self._class_names = []

    def start(self) -> None:
        if self._yamnet is None or self._sd is None:
            return

        self._stop_event.clear()
        self._audio_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._infer_thread = threading.Thread(target=self._infer_loop, daemon=True)
        self._audio_thread.start()
        self._infer_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._audio_thread:
            self._audio_thread.join(timeout=2.0)
        if self._infer_thread:
            self._infer_thread.join(timeout=2.0)

    def get_latest_signal(self, timeout: float = 0.2) -> Optional[AudioSignal]:
        try:
            return self._signal_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _capture_loop(self) -> None:
        sd = self._sd
        assert sd is not None

        while not self._stop_event.is_set():
            chunk = sd.rec(self.chunk_samples, samplerate=self.sample_rate, channels=1, dtype="float32")
            sd.wait()
            arr = np.squeeze(chunk, axis=1)
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
            self._queue.put_nowait(arr)

    def _infer_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                wave = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            signal = self._classify(wave)
            self._window.append(signal)
            smoothed = self._smooth_signal(list(self._window))

            if self._signal_queue.full():
                try:
                    self._signal_queue.get_nowait()
                except queue.Empty:
                    pass
            self._signal_queue.put_nowait(smoothed)

    def _classify(self, waveform: np.ndarray) -> AudioSignal:
        if self._yamnet is None:
            return AudioSignal(audio_event="silence", confidence=0.0, timestamp=time.time())

        scores, _, _ = self._yamnet(waveform)
        scores_np = np.array(scores)
        mean_scores = np.mean(scores_np, axis=0)
        idx = int(np.argmax(mean_scores))

        label = self._class_names[idx] if idx < len(self._class_names) else "Unknown"
        mapped = self._map_label(label)
        conf = float(mean_scores[idx])
        return AudioSignal(audio_event=mapped, confidence=conf, timestamp=time.time())

    def _map_label(self, label: str) -> str:
        for key, value in self.TARGET_LABEL_MAP.items():
            if key.lower() in label.lower():
                return value
        return "ambient"

    @staticmethod
    def _smooth_signal(window: List[AudioSignal]) -> AudioSignal:
        if not window:
            return AudioSignal(audio_event="ambient", confidence=0.0, timestamp=time.time())

        by_label: Dict[str, float] = {}
        for s in window:
            by_label[s.audio_event] = by_label.get(s.audio_event, 0.0) + s.confidence

        best_label = max(by_label.items(), key=lambda x: x[1])[0]
        avg_conf = by_label[best_label] / max(1, sum(1 for s in window if s.audio_event == best_label))
        return AudioSignal(audio_event=best_label, confidence=float(avg_conf), timestamp=window[-1].timestamp)
