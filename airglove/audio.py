"""Optional microphone transient confirmation for the IMU snap."""

from collections import deque
import time


class Transients:
    def __init__(self):
        self.last_peak = 0.02
        self.events = deque(maxlen=16)

    def feed(self, samples, stamp):
        if not samples:
            return
        peak = max(map(abs, samples)) / 32768
        rms = (sum(value * value for value in samples) / len(samples)) ** 0.5 / 32768
        if peak >= max(0.06, self.last_peak * 2.8) and peak >= 3.2 * rms:
            self.events.append(stamp)
        self.last_peak = 0.88 * self.last_peak + 0.12 * peak

    def near(self, stamp):
        return any(abs(stamp - event) <= 0.11 for event in tuple(self.events))


class Microphone:
    def __init__(self):
        self.detector = Transients()
        self.stream = None

    def open(self):
        import sounddevice

        self.detector = Transients()

        def capture(data, _frames, _timing, _status):
            self.detector.feed(memoryview(data).cast("h"), time.monotonic())

        self.stream = sounddevice.RawInputStream(channels=1, dtype="int16", blocksize=480, callback=capture)
        try:
            self.stream.start()
        except Exception:
            self.stream.close()
            self.stream = None
            raise

    def close(self):
        if self.stream is not None:
            try:
                self.stream.close()
            finally:
                self.stream = None
