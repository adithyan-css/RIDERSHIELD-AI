import threading

import pyttsx3


class TTSEngine:
    """Thread-safe wrapper around offline pyttsx3 engine."""

    def __init__(self, speech_rate: int = 185) -> None:
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", speech_rate)
        self._lock = threading.Lock()

    def speak_blocking(self, text: str) -> None:
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()

    def stop(self) -> None:
        with self._lock:
            self._engine.stop()
