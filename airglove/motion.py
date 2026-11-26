"""Host-side orientation, pose classification and mouse gestures."""

from dataclasses import dataclass
import math

from .protocol import ACCEL_SCALE, CALIBRATING, CHANNELS, GYRO_SCALE, elapsed_ms

UP = (0.0, 0.0, 1.0)
GRAVITY = 9.80665
FINGER_SPREAD = (-40, -8, 0, 8, 15)
STRAIGHT_ANGLE = 27
BENT_ANGLE = 42


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def scale(vector, factor):
    return tuple(component * factor for component in vector)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    ax, ay, az = a
    bx, by, bz = b
    return ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx


def norm(vector):
    return math.sqrt(dot(vector, vector))


def unit(vector):
    length = norm(vector)
    return scale(vector, 1 / length) if length > 1e-8 else None


def transpose(matrix):
    return tuple(zip(*matrix))


def transform(matrix, vector):
    return tuple(dot(row, vector) for row in matrix)


def orientation(accel, mag):
    """Rows are the world axes expressed in sensor coordinates."""
    up = unit(accel)
    east = unit(cross(up, mag))
    if east is None:
        # With no heading, assume the sensor was mounted with matching axes.
        axis = (1, 0, 0) if abs(up[0]) < 0.9 else (0, 1, 0)
        east = unit(cross(up, axis))
    return cross(east, up), east, up


@dataclass
class SensorPose:
    reference: tuple
    rotation: tuple
    gyro_bias: tuple

    def update(self, sample, dt):
        gyro = scale(subtract(sample.gyro, self.gyro_bias), math.pi / (180 * GYRO_SCALE))
        speed = norm(gyro)
        heading, _, up = self.rotation
        if speed < math.radians(1.3):
            gyro = (0, 0, 0)
        elif dt:
            axis = scale(gyro, 1 / speed)
            cosine, sine = math.cos(speed * dt), math.sin(speed * dt)

            def rotate(row):
                return add(subtract(scale(row, cosine), scale(cross(axis, row), sine)),
                           scale(axis, dot(axis, row) * (1 - cosine)))

            heading, up = rotate(heading), rotate(up)
        accel = scale(sample.accel, 1 / ACCEL_SCALE)
        measured_up = unit(accel)
        # Gravity corrects tilt. Small weight keeps transients from looking like tilt.
        if measured_up is not None and abs(norm(accel) - GRAVITY) < 1 and dot(up, measured_up) > 0.3:
            weight = 1 - math.exp(-dt / 0.30)
            up = unit(add(scale(up, 1 - weight), scale(measured_up, weight)))
        east = unit(cross(up, heading))
        self.rotation = cross(east, up), east, up
        linear = subtract(transform(self.rotation, accel), scale(UP, GRAVITY))
        return transform(self.rotation, gyro), linear

    def direction(self, neutral):
        return transform(self.rotation, transform(transpose(self.reference), neutral))


class StationaryWindow:
    def __init__(self):
        self.clear()

    def clear(self):
        self.start = None
        self.count = 0
        self.first = None
        self.sums = [(0, 0, 0)] * 3

    def collect(self, sample, stamp):
        if sample is None or not 850 < norm(sample.accel) < 1100 or norm(sample.gyro) > 8 * GYRO_SCALE:
            self.clear()
            return
        if self.first is not None and norm(subtract(sample.accel, self.first)) > 75:
            self.clear()
        if self.start is None:
            self.start = stamp
            self.first = sample.accel
        self.count += 1
        self.sums = [add(total, values) for total, values in
                     zip(self.sums, (sample.accel, sample.gyro, sample.mag))]

    def pose(self, stamp):
        if self.count < 4 or elapsed_ms(stamp, self.start) < 750:
            return None
        accel, gyro, mag = (scale(vector, 1 / self.count) for vector in self.sums)
        basis = orientation(accel, mag)
        return SensorPose(basis, basis, gyro)


@dataclass(frozen=True)
class Action:
    dx: float = 0
    dy: float = 0
    wheel: int = 0
    click: str | None = None


class Motion:
    def __init__(self):
        self.poses = [None] * CHANNELS
        self.directions = [None] * CHANNELS
        self.extended = [None] * (CHANNELS - 1)
        self.forward = (0, 1, 0)
        self.right = (1, 0, 0)
        self.previous_stamp = None
        self.windows = None
        self.calibration_start = None
        self.calibration = "idle"
        self.last_valid = 0
        self.rates = None
        self._reset_gesture()

    def _reset_gesture(self):
        self.candidate = None
        self.stable = None
        self.pose_since = None
        self.scroll_at = None
        self.click_sent = False
        self.scroll_ready = False
        self.click_blocked = False

    @property
    def ready(self):
        return self.calibration == "ready" and self.last_valid == (1 << CHANNELS) - 1

    def calibrate(self):
        self.windows = [StationaryWindow() for _ in range(CHANNELS)]
        self.calibration_start = None
        self.calibration = "collecting"
        self.poses = [None] * CHANNELS
        self.extended = [None] * (CHANNELS - 1)
        self.directions = [None] * CHANNELS
        self.rates = None
        self._reset_gesture()

    def align_heading(self):
        palm = self.poses[0]
        if palm is None:
            return False
        x, y, _ = transform(palm.reference, palm.rotation[2])
        if math.hypot(x, y) < 0.25:
            return False
        self.forward = unit((x, y, 0))
        self.right = cross(self.forward, UP)
        self._reset_gesture()
        return True

    def _collect(self, frame):
        if frame.flags & CALIBRATING:
            self.calibration_start = None
            self.windows = [StationaryWindow() for _ in range(CHANNELS)]
            return
        if self.calibration_start is None:
            self.calibration_start = frame.millis
        for window, sample in zip(self.windows, frame.samples):
            window.collect(sample, frame.millis)
        if elapsed_ms(frame.millis, self.calibration_start) < 1250:
            return
        self.poses = [window.pose(frame.millis) for window in self.windows]
        self.windows = None
        if self.poses[0] is None:
            self.calibration = "failed"
            return
        palm = self.poses[0].reference
        candidate = transform(palm, (0, 1, 0))
        forward = unit((candidate[0], candidate[1], 0)) if abs(candidate[2]) < 0.9 else None
        self.forward = forward or (0, 1, 0)
        self.right = cross(self.forward, UP)
        self.calibration = "ready" if all(self.poses) else "partial"

    def feed(self, frame, sensitivity=1):
        self.last_valid = frame.valid
        self.rates = None
        if self.windows is not None:
            self._collect(frame)
        delta = 0 if self.previous_stamp is None else elapsed_ms(frame.millis, self.previous_stamp)
        self.previous_stamp = frame.millis
        if delta > 350 or frame.flags & CALIBRATING:
            # A stale orientation cannot be integrated across a large gap.
            if self.windows is None and self.calibration in ("ready", "partial"):
                self.poses = [None] * CHANNELS
                self.directions = [None] * CHANNELS
                self.extended = [None] * (CHANNELS - 1)
                self.calibration = "idle"
                self._reset_gesture()
            return Action()
        dt = delta / 1000
        rates = [None] * CHANNELS
        self.directions = [None] * CHANNELS
        for channel, (pose, sample) in enumerate(zip(self.poses, frame.samples)):
            if pose is None or sample is None:
                # The sensor may rotate while absent. Require a new reference on recovery.
                if pose is not None:
                    self.poses[channel] = None
                    self.calibration = "partial"
                continue
            rates[channel] = pose.update(sample, dt)
            neutral = self.forward
            if channel:
                spread = math.radians(FINGER_SPREAD[channel - 1])
                neutral = add(scale(self.forward, math.cos(spread)), scale(self.right, math.sin(spread)))
            self.directions[channel] = pose.direction(neutral)
            if channel:
                palm = self.poses[0]
                angle_cos = dot(self.directions[channel], palm.direction(neutral)) if palm else -1
                old = self.extended[channel - 1]
                threshold = BENT_ANGLE if old else STRAIGHT_ANGLE
                self.extended[channel - 1] = angle_cos >= math.cos(math.radians(threshold)) if palm else None
        for index, direction in enumerate(self.directions[1:]):
            if direction is None:
                self.extended[index] = None
        if not self.ready:
            self._reset_gesture()
            return Action()
        self.rates = rates
        return self._gesture(frame.millis, dt, rates, sensitivity)

    def _gesture(self, stamp, dt, rates, sensitivity):
        fingers = tuple(index for index, extended in enumerate(self.extended, 1) if extended)
        if fingers != self.candidate:
            self.candidate = fingers
            self.pose_since = stamp
            self.stable = None
            self.click_sent = False
            self.click_blocked = False
            self.scroll_ready = False
        age = elapsed_ms(stamp, self.pose_since)
        if age < 80:
            return Action()
        self.stable = fingers
        if len(fingers) == 1:
            channel = fingers[0]
            gyro, linear = rates[channel]
            velocity = cross(gyro, self.directions[channel])
            x = dot(velocity, self.right) * 950
            y = -velocity[2] * 950
            # A short translational push also contributes above the noise floor.
            if norm(linear) > 2.2:
                x += dot(linear, self.right) * 50
                y += (-linear[2] * 50 - dot(linear, self.forward) * 28)
            return Action(dx=max(-140, min(140, x * dt * sensitivity)),
                          dy=max(-140, min(140, y * dt * sensitivity)))
        if len(fingers) >= 2:
            vertical = rates[0][1][2]
            if abs(vertical) < 1.1:
                self.scroll_ready = True
            if abs(vertical) >= 2.6:
                self.click_blocked = True
                if self.scroll_ready and (self.scroll_at is None or elapsed_ms(stamp, self.scroll_at) >= 450):
                    self.scroll_at = stamp
                    self.scroll_ready = False
                    return Action(wheel=1 if vertical > 0 else -1)
            if fingers in ((1, 2), (1, 3)) and age >= 260 and not (self.click_sent or self.click_blocked):
                self.click_sent = True
                return Action(click="left" if fingers == (1, 2) else "right")
        return Action()
