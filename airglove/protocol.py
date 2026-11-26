"""AirGlove v1 and compatibility with AirGloveCheck serial logs."""

import base64
import binascii
import codecs
from dataclasses import dataclass
import re
import struct
import time

SERVICE = "8d032000-1a92-4e8d-a5a2-fbeac12bb201"
TELEMETRY = "8d032001-1a92-4e8d-a5a2-fbeac12bb201"
CHANNELS = 6
ALL_CHANNELS = (1 << CHANNELS) - 1
CALIBRATING = 1
BATTERY_LOW = 2
BATTERY_UNKNOWN = 0xFFFF
ACCEL_SCALE = 100
GYRO_SCALE = 16
HEADER = struct.Struct("<2sBBHIBBH")
SAMPLES = struct.Struct("<54h")
CRC = struct.Struct("<H")
FRAME_SIZE = HEADER.size + SAMPLES.size + CRC.size
FRAGMENT = struct.Struct("<BHB")
LEGACY = re.compile(
    r"CH([0-5])\s+\w+\s+ACC=\((-?\d+),(-?\d+),(-?\d+)\)"
    r"\s+GYR=\((-?\d+),(-?\d+),(-?\d+)\)"
    r"\s+MAG=\((-?\d+),(-?\d+),(-?\d+)\)"
)
LEGACY_FAILURE = re.compile(r"CH([0-5])\s+\w+\s+FAIL I2C read")
MONITOR_TIME = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+->\s+")


@dataclass(frozen=True)
class Sample:
    accel: tuple[int, int, int]
    gyro: tuple[int, int, int]
    mag: tuple[int, int, int]


@dataclass(frozen=True)
class Frame:
    sequence: int
    millis: int
    samples: tuple[Sample | None, ...]
    biased: int = 0
    flags: int = 0
    battery_mv: int = BATTERY_UNKNOWN

    @property
    def valid(self):
        return sum(1 << i for i, sample in enumerate(self.samples) if sample is not None)


def encode(frame):
    head = HEADER.pack(b"AG", 1, frame.flags, frame.sequence, frame.millis,
                       frame.valid, frame.biased, frame.battery_mv)
    values = []
    for sample in frame.samples:
        values.extend(sample.accel + sample.gyro + sample.mag if sample else (0,) * 9)
    payload = head + SAMPLES.pack(*values)
    return payload + CRC.pack(binascii.crc_hqx(payload, 0xFFFF))


def decode(data):
    if len(data) != FRAME_SIZE:
        raise ValueError("Неверная длина кадра")
    signature, version, flags, sequence, millis, valid, biased, battery = HEADER.unpack_from(data)
    if signature != b"AG" or version != 1 or (valid | biased) & ~ALL_CHANNELS:
        raise ValueError("Неизвестный формат кадра")
    if CRC.unpack_from(data, FRAME_SIZE - CRC.size)[0] != binascii.crc_hqx(data[:-CRC.size], 0xFFFF):
        raise ValueError("Неверная контрольная сумма")
    values = SAMPLES.unpack_from(data, HEADER.size)
    samples = []
    for channel in range(CHANNELS):
        start = channel * 9
        samples.append(Sample(values[start:start + 3], values[start + 3:start + 6],
                              values[start + 6:start + 9]) if valid & (1 << channel) else None)
    return Frame(sequence, millis, tuple(samples), biased, flags, battery)


def serial_line(frame):
    return b"AG1 " + base64.b64encode(encode(frame)) + b"\n"


def elapsed_ms(current, previous):
    return (current - previous) & 0xFFFFFFFF


class Fragments:
    """Reassemble ordered notifications and discard incomplete or corrupt frames."""

    def __init__(self):
        self.payload = bytearray()
        self.sequence = None

    def feed(self, packet):
        if len(packet) <= FRAGMENT.size:
            return None
        marker, sequence, offset = FRAGMENT.unpack_from(packet)
        if marker != 0xAF:
            return None
        if offset == 0:
            self.sequence = sequence
            self.payload.clear()
        if sequence != self.sequence or offset != len(self.payload):
            return None
        self.payload.extend(packet[FRAGMENT.size:])
        if len(self.payload) < FRAME_SIZE:
            return None
        self.sequence = None
        try:
            frame = decode(self.payload)
        except ValueError:
            return None
        return frame if frame.sequence == sequence else None


class SerialFrames:
    def __init__(self):
        self.channels = {}
        self.sequence = 0
        self.stamp = 0

    def feed(self, line, stamp=None, *, timed=False):
        line = line.strip()
        if line.startswith("AG1 "):
            try:
                return decode(base64.b64decode(line[4:], validate=True))
            except (ValueError, binascii.Error):
                return None
        match = LEGACY.fullmatch(line)
        failure = LEGACY_FAILURE.fullmatch(line)
        if not (match or failure):
            return None
        channel = int((match or failure)[1])
        completed = None
        if self.channels and (channel <= max(self.channels) or
                              (timed and elapsed_ms(stamp, self.stamp) >= 120)):
            completed = self.flush()
        if not self.channels:
            if stamp is None:
                stamp = int(time.monotonic() * 1000)
            self.stamp = stamp & 0xFFFFFFFF
        if match:
            values = tuple(map(int, match.groups()[1:]))
            if all(-32768 <= value <= 32767 for value in values):
                self.channels[channel] = Sample(values[:3], values[3:6], values[6:])
        else:
            self.channels[channel] = None
        return completed

    def flush(self):
        if not self.channels:
            return None
        frame = Frame(self.sequence, self.stamp, tuple(self.channels.get(i) for i in range(CHANNELS)))
        self.channels.clear()
        self.sequence = (self.sequence + 1) & 0xFFFF
        return frame


def read_recording(path):
    """Read AG1 frames or grouped text readings from the diagnostic sketch."""
    parser = SerialFrames()
    with open(path, "rb") as binary:
        bom = binary.read(2)
    encoding = "utf-16" if bom in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE) else "utf-8-sig"
    previous_time = None
    midnight = 0
    with open(path, encoding=encoding, errors="replace") as recording:
        for line in recording:
            timestamp = MONITOR_TIME.match(line)
            if timestamp:
                hours, minutes, seconds, millis = map(int, timestamp.groups())
                current = ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis
                day = 24 * 60 * 60 * 1000
                if previous_time is not None and previous_time - current > day // 2:
                    midnight += day
                previous_time = current
                frame = parser.feed(line[timestamp.end():], current + midnight, timed=True)
            else:
                frame = parser.feed(line, (parser.sequence + bool(parser.channels)) * 250)
            if frame is not None:
                yield frame
        last_frame = parser.flush()
        if last_frame is not None:
            yield last_frame
