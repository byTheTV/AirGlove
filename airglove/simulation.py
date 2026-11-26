"""Repeatable 50 Hz sensor input for a demo, recording, and offline testing."""

import math

from .motion import FINGER_SPREAD, GRAVITY, UP, add, cross, scale, transform, transpose
from .protocol import ALL_CHANNELS, BATTERY_LOW, Frame, Sample
from .training import PRACTICE_GESTURES

RATE = 50
STEP_MS = 1000 // RATE
SECTIONS = (
    "Нейтральная поза", "Курсор указательным пальцем", "Тычок",
    "Прокрутка вверх", "Прокрутка вниз", "Левый клик", "Правый клик",
    "Кулак в движении", "Обрыв датчика", "Возврат датчика",
)
PHASE_LENGTH = 2.5
LOOP_SECONDS = PHASE_LENGTH * len(SECTIONS)
POSES = (
    (0, 0, 0, 0, 0), (72, 0, 72, 72, 72), (72, 0, 72, 72, 72),
    (72, 0, 0, 72, 72), (72, 0, 0, 72, 72),
    (0, 0, 72, 72, 72), (0, 72, 0, 72, 72),
    (72, 72, 72, 72, 72), (0, 0, 0, 0, 0), (0, 0, 0, 0, 0),
)
PRACTICE_FIRST = 1.65
PRACTICE_STEP = 0.40
PRACTICE_SNAP = 6.25
PRACTICE_DURATION = 7.6


def rotation_x(angle):
    c, s = math.cos(angle), math.sin(angle)
    return (1, 0, 0), (0, c, -s), (0, s, c)


def rotation_z(angle):
    c, s = math.cos(angle), math.sin(angle)
    return (c, -s, 0), (s, c, 0), (0, 0, 1)


def product(a, b):
    return transpose(tuple(transform(a, column) for column in transpose(b)))


def phase(seconds):
    local = seconds % LOOP_SECONDS
    return divmod(local, PHASE_LENGTH)


def hump(seconds, start, duration):
    progress = (seconds - start) / duration
    return math.sin(math.pi * progress) ** 2 if 0 < progress < 1 else 0


def matrices(seconds):
    section, local = phase(seconds)
    index = int(section)
    blend = min(1, local / 0.45)
    blend = blend * blend * (3 - 2 * blend)
    yaw = math.radians(35) * hump(local, 0.8, 1.45) if index in (1, 7) else 0
    pitch = math.radians(16) * hump(local, 0.57, 0.8) if index in (1, 7) else 0
    palm = product(rotation_z(yaw), rotation_x(pitch))
    angles = [POSES[index - 1][i] * (1 - blend) + POSES[index][i] * blend for i in range(5)]
    return hand_matrices(palm, angles)


def hand_matrices(palm, angles):
    result = [palm]
    for channel, (spread_degrees, flex_degrees) in enumerate(zip(FINGER_SPREAD, angles)):
        spread = math.radians(spread_degrees)
        angle = math.radians(flex_degrees)
        flex = product(product(rotation_z(-spread), rotation_x(-angle)), rotation_z(spread))
        mounting = rotation_z(math.radians(12 * channel))
        result.append(product(product(palm, flex), mounting))
    return result


def frame_at(index):
    seconds = index / RATE
    section, local = phase(seconds)
    current = matrices(seconds)
    previous = matrices(max(0, seconds - 1 / RATE))
    accelerations = [scale(UP, GRAVITY)] * 6
    if section == 2:
        pulse = hump(local, 1, 0.22) - hump(local, 1.22, 0.22)
        accelerations[2] = add(accelerations[2], (4 * pulse, 4 * pulse, 0))
    if section in (3, 4):
        pulse = hump(local, 1, 0.24) - hump(local, 1.25, 0.24)
        accelerations = [scale(UP, GRAVITY + pulse * (4 if section == 3 else -4))] * 6
    return sampled_frame(index, current, previous, accelerations, missing=4 if section == 8 else None)


def practice_matrices(seconds):
    angles = [0] * 5
    for index, finger in enumerate(PRACTICE_GESTURES):
        start = PRACTICE_FIRST + index * PRACTICE_STEP
        angles[abs(finger) - 1] += (30 if finger > 0 else -30) * hump(seconds, start, 0.24)
    angles[0] += 36 * hump(seconds, PRACTICE_SNAP, 0.22)
    angles[2] += 72 * hump(seconds, PRACTICE_SNAP + 0.02, 0.29)
    return hand_matrices(rotation_x(0), angles)


def practice_frame_at(index):
    seconds = index / RATE
    current = practice_matrices(seconds)
    previous = practice_matrices(max(0, seconds - 1 / RATE))
    accelerations = [scale(UP, GRAVITY)] * 6
    impact = 5 * hump(seconds, PRACTICE_SNAP + 0.045, 0.12)
    accelerations[3] = (impact, 0, GRAVITY)
    return sampled_frame(index, current, previous, accelerations)


def sampled_frame(index, current, previous, accelerations, missing=None):
    samples = []
    for channel, (before, after) in enumerate(zip(previous, current)):
        if channel == missing:
            samples.append(None)
            continue
        world_omega = (0, 0, 0)
        for old_axis, new_axis in zip(transpose(before), transpose(after)):
            world_omega = add(world_omega, cross(old_axis, new_axis))
        sensor_axes = transpose(after)
        accel = tuple(round(v * 100) for v in transform(sensor_axes, accelerations[channel]))
        gyro = tuple(round(v * (RATE / 2) * math.degrees(1) * 16)
                     for v in transform(sensor_axes, world_omega))
        mag = tuple(round(v) for v in transform(sensor_axes, (450, 0, 275)))
        samples.append(Sample(accel, gyro, mag))
    battery = 3320 if missing is not None else 3900
    biased = ALL_CHANNELS ^ (1 << missing) if missing is not None else ALL_CHANNELS
    flags = BATTERY_LOW if missing is not None else 0
    return Frame(index & 0xFFFF, index * STEP_MS & 0xFFFFFFFF, tuple(samples), biased, flags, battery)
