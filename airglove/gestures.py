"""Short finger taps and a two-finger snap, independent of assigned actions."""

import math

from .motion import UP, dot, norm, subtract
from .protocol import elapsed_ms


class Tap:
    def __init__(self):
        self.start = None
        self.peak = 0
        self.neutral = False

    def sample(self, angle, stamp):
        size = abs(angle)
        if size <= 7:
            result = None
            if self.start is not None and 45 <= elapsed_ms(stamp, self.start) <= 300:
                if 15 <= abs(self.peak) <= 56:
                    result = 1 if self.peak > 0 else -1
            self.start = None
            self.neutral = True
            return result
        if self.neutral and size >= 10:
            self.start, self.peak, self.neutral = stamp, angle, False
        elif self.start is not None and size > abs(self.peak):
            self.peak = angle
        return None


class FingerGestures:
    def __init__(self):
        self.reset()

    def reset(self):
        self.taps = [Tap() for _ in range(5)]
        self.previous = None
        self.thumb = None
        self.middle = None
        self.pending = None
        self.last_snap = None
        self.last_tap = [None] * 5

    def feed(self, stamp, motion, audio=None):
        if motion.rates is None:
            self.reset()
            return ()
        palm_up = motion.poses[0].direction(UP)
        palm_gyro, palm_accel = motion.rates[0]
        angles = [math.degrees(math.asin(max(-1, min(1, -dot(direction, palm_up)))))
                  for direction in motion.directions[1:]]
        angular = [math.degrees(norm(subtract(gyro, palm_gyro))) for gyro, _ in motion.rates[1:]]
        impulse = [norm(subtract(accel, palm_accel)) for _, accel in motion.rates[1:]]
        quiet = math.degrees(norm(palm_gyro)) < 140 and norm(palm_accel) < 4.5
        return self.sample(stamp, angles, angular, impulse, quiet, audio)

    def sample(self, stamp, angles, angular, impulse, quiet, audio=None):
        if self.previous is not None and elapsed_ms(stamp, self.previous) > 85:
            self.reset()
        self.previous = stamp
        taps = []
        for index, (detector, angle) in enumerate(zip(self.taps, angles)):
            result = detector.sample(angle, stamp)
            if result == 1 or (result == -1 and index == 1):
                last = self.last_tap[index]
                if last is None or elapsed_ms(stamp, last) >= 85:
                    taps.append((index, f"tap_{index + 1}" if result == 1 else "lift_2"))

        if quiet and (self.last_snap is None or elapsed_ms(stamp, self.last_snap) >= 700):
            if angular[0] >= 175:
                self.thumb = stamp
            if angular[2] >= 330 and angles[2] >= 14 and impulse[2] >= 1.8:
                self.middle = stamp
            if self.thumb is not None and self.middle is not None:
                if elapsed_ms(stamp, self.thumb) <= 75 and elapsed_ms(stamp, self.middle) <= 75:
                    self.pending = stamp
                    self.thumb = self.middle = None
        if self.pending is not None:
            if elapsed_ms(stamp, self.pending) > 100:
                self.pending = None
            elif audio is not False:
                self.pending = None
                self.last_snap = stamp
                self.taps = [Tap() for _ in range(5)]
                return ("snap",)
            else:
                return ()
        if self.last_snap is not None and elapsed_ms(stamp, self.last_snap) < 220:
            return ()
        if len(taps) == 1:
            index, name = taps[0]
            self.last_tap[index] = stamp
            return (name,)
        return ()
