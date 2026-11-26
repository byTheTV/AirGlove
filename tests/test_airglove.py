import asyncio
from collections import Counter
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import threading
import unittest

from airglove.motion import Action, Motion
from airglove.mouse import BUTTONS, MOVE, WHEEL, WindowsMouse
from airglove.protocol import (
    ALL_CHANNELS, CALIBRATING, FRAME_SIZE, Fragments, SerialFrames, decode, elapsed_ms,
    encode, read_recording, serial_line,
)
from airglove.simulation import LOOP_SECONDS, RATE, frame_at, phase
from airglove.sources import _listen_ble, _read_usb, replay


def packets(frame, mtu):
    payload = encode(frame)
    span = mtu - 7
    return [struct.pack("<BHB", 0xAF, frame.sequence, offset) + payload[offset:offset + span]
            for offset in range(0, len(payload), span)]


class ProtocolTests(unittest.TestCase):
    def test_round_trip_crc_and_missing_channel(self):
        frame = replace(frame_at(1007), sequence=65535, millis=0xFFFFFFFF)
        wire = encode(frame)
        self.assertEqual(len(wire), FRAME_SIZE)
        self.assertIsNone(frame.samples[4])
        self.assertEqual(decode(wire), frame)
        self.assertEqual(SerialFrames().feed(serial_line(frame).decode("ascii")), frame)
        self.assertEqual(elapsed_ms(19, frame.millis), 20)
        broken = bytearray(wire)
        broken[56] ^= 0x01
        with self.assertRaises(ValueError):
            decode(broken)

    def test_mtu_and_missing_fragments(self):
        frame = frame_at(48)
        for mtu in (23, 64, 131, 185):
            reader = Fragments()
            results = [reader.feed(packet) for packet in packets(frame, mtu)]
            self.assertEqual([frame], [result for result in results if result is not None])
        damaged = packets(frame, 23)
        reader = Fragments()
        for packet in damaged[:1] + damaged[2:]:
            self.assertIsNone(reader.feed(packet))
        recovered = frame_at(49)
        for packet in packets(recovered, 23):
            result = reader.feed(packet)
        self.assertEqual(result, recovered)

    def test_legacy_recording_with_timestamps_and_explicit_failure(self):
        contents = (
            "19:00:00.000 -> AirGlove diagnostics\n"
            "19:00:00.001 -> CH0 hand ACC=(0,0,981) GYR=(-1,0,0) MAG=(4,7,9)\n"
            "19:00:00.002 -> CH3 middle ACC=(7,5,982) GYR=(0,2,3) MAG=(0,10,25)\n"
            "19:00:00.002 -> CH6 reserve ACC=(7,5,982) GYR=(0,2,3) MAG=(0,10,25)\n"
            "19:00:00.251 -> CH0 hand ACC=(0,0,980) GYR=(0,0,0) MAG=(4,7,9)\n"
            "19:00:00.252 -> CH3 middle FAIL I2C read\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "old.txt"
            path.write_text(contents, encoding="utf-16")
            first, second = read_recording(path)
        self.assertEqual(first.valid, (1 << 0) | (1 << 3))
        self.assertEqual(first.samples[0].gyro, (-1, 0, 0))
        self.assertEqual(second.valid, 1)
        self.assertEqual(second.millis - first.millis, 250)

    def test_record_replay(self):
        frames = [frame_at(index) for index in range(3)]
        events = []
        with tempfile.TemporaryDirectory() as temp:
            single = Path(temp) / "sample.aglog"
            single.write_bytes(b"".join(map(serial_line, frames)))
            replay(lambda kind, data: events.append((kind, data)), threading.Event(), single)
        self.assertEqual([data for kind, data in events if kind == "frame"], frames)
        self.assertEqual(events[-1][0], "ended")


class MotionTests(unittest.TestCase):
    def test_all_gestures_for_three_minutes(self):
        motion = Motion()
        motion.calibrate()
        effects = Counter()
        for index in range(180 * RATE):
            frame = decode(encode(frame_at(index)))
            if motion.calibration == "partial" and frame.valid == ALL_CHANNELS:
                motion.calibrate()
            action = motion.feed(frame)
            cycle = int(index / RATE // LOOP_SECONDS)
            section = int(phase(index / RATE)[0])
            if action.click:
                effects[cycle, section, action.click] += 1
            if action.wheel:
                effects[cycle, section, action.wheel] += 1
            if action.dx or action.dy:
                effects[cycle, section, "move"] += 1
            if section == 8:
                self.assertFalse(motion.ready)
        for cycle in range(7):
            for section in (1, 2):
                self.assertGreater(effects[cycle, section, "move"], 5)
            for section, action in ((3, 1), (4, -1), (5, "left"), (6, "right")):
                self.assertEqual(effects[cycle, section, action], 1)
        self.assertTrue(all(section in range(1, 7) for _, section, _ in effects))

    def test_stationary_calibration_and_gap_disarm(self):
        motion = Motion()
        motion.calibrate()
        for index in range(100):
            motion.feed(replace(frame_at(index), flags=CALIBRATING))
        self.assertFalse(motion.ready)
        for index in range(100):
            frame = replace(frame_at(0), millis=2000 + index * 20)
            self.assertEqual(motion.feed(frame), Action())
        self.assertTrue(motion.ready)
        self.assertEqual(motion.feed(replace(frame, millis=4500)), Action())
        self.assertFalse(motion.ready)
        self.assertEqual(motion.calibration, "idle")

    def test_reject_motion_during_calibration(self):
        motion = Motion()
        motion.calibrate()
        frame = frame_at(0)
        moving = tuple(replace(sample, gyro=(240, -100, 5)) for sample in frame.samples)
        for index in range(90):
            motion.feed(replace(frame, millis=index * 20, samples=moving))
        self.assertFalse(motion.ready)
        self.assertEqual(motion.calibration, "failed")


class TransportTests(unittest.TestCase):
    def test_usb_handles_split_lines(self):
        frame = frame_at(4)
        line = serial_line(frame)
        stop = threading.Event()
        chunks = iter((b"startup\r\n", line[:78], line[78:]))
        events = []

        class Port:
            def read_until(self, size):
                chunk = next(chunks, b"")
                if not chunk:
                    stop.set()
                return chunk

        _read_usb(lambda kind, data: events.append((kind, data)), stop, Port())
        self.assertEqual(events, [("frame", frame)])

    def test_ble_notification_transport_reports_disconnect(self):
        frame = frame_at(8)
        events = []

        class Client:
            is_connected = True

            def __init__(self, _device, disconnected_callback, timeout):
                self.disconnect = disconnected_callback

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                self.is_connected = False

            async def start_notify(self, _uuid, callback):
                for packet in packets(frame, 23):
                    callback(None, packet)
                self.disconnect(self)

        class Device:
            name = "AirGlove"

        asyncio.run(_listen_ble(Client, Device(), lambda kind, data: events.append((kind, data))))
        self.assertEqual([kind for kind, _ in events], ["status", "reset", "frame", "reset"])
        self.assertEqual(events[2][1], frame)


class MouseTests(unittest.TestCase):
    def test_windows_output_accumulates_movement_and_pairs_clicks(self):
        events = []

        class FakeUser32:
            def SendInput(self, count, batch, _size):
                for index in range(count):
                    mouse = batch[index].mouse
                    events.append((mouse.flags, mouse.dx, mouse.dy, mouse.mouseData))
                return count

        mouse = object.__new__(WindowsMouse)
        mouse.api = FakeUser32()
        mouse.reset()
        mouse.apply(Action(dx=0.5, dy=-0.5))
        self.assertEqual(events, [])
        mouse.apply(Action(dx=0.5, dy=-0.5, wheel=-1, click="right"))
        press, release = BUTTONS["right"]
        self.assertEqual(events, [(MOVE, 1, -1, 0), (WHEEL, 0, 0, 0xFFFFFF88),
                                  (press, 0, 0, 0), (release, 0, 0, 0)])


if __name__ == "__main__":
    unittest.main()
