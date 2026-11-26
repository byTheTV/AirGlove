import ctypes
from pathlib import Path
import tempfile
import unittest

from airglove.audio import Transients
from airglove.gestures import FingerGestures
from airglove.motion import Motion
from airglove.mouse import Input, KEYS, KEY_EXTENDED, KEY_SCAN, KEY_UP, WindowsMouse
from airglove.profiles import Binding, ProfileBook, new_profile
from airglove.protocol import decode, encode
from airglove.simulation import PRACTICE_DURATION, RATE, practice_frame_at
from airglove.training import PRACTICE_KEYS, Training


class ProfilesTests(unittest.TestCase):
    def test_create_edit_activate_cycle_and_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, "profile.json")
            book = ProfileBook(path)
            self.assertEqual(book.current.id, "desktop")
            profile = new_profile("Моя перчатка", {"tap_3": Binding("key", "Space")})
            book.save(profile)
            book.activate(profile.id)
            self.assertEqual(book.cycle().id, "desktop")
            loaded = ProfileBook(path)
            self.assertEqual(loaded.current, profile)
            loaded.delete(profile.id)
            self.assertEqual(ProfileBook(path).current.id, "desktop")

    def test_corrupt_file_is_backed_up_before_edit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, "profile.json")
            original = b'{"version":1,"profiles":[{"id":"x","name":"x","bindings":[]}]}'
            path.write_bytes(original)
            book = ProfileBook(path)
            self.assertIsNotNone(book.error)
            book.save(new_profile("Исправленный"))
            self.assertEqual(book.backup.read_bytes(), original)
            self.assertIsNone(ProfileBook(path).error)

    def test_invalid_key_leaves_preexisting_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, "profile.json")
            book = ProfileBook(path)
            book.activate("invoker")
            previous = path.read_bytes()
            invalid = new_profile("Ошибка", {"tap_3": Binding("key", "WWQ")})
            with self.assertRaises(ValueError):
                book.save(invalid)
            self.assertEqual(path.read_bytes(), previous)


class GesturesTests(unittest.TestCase):
    def test_practice_telemetry_maps_every_key_and_cycles_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            book = ProfileBook(Path(temp, "profile.json"))
            book.active = "invoker"
            recognizer, motion = FingerGestures(), Motion()
            motion.calibrate()
            exercise = Training()
            mapped = []
            for index in range(round(PRACTICE_DURATION * RATE)):
                frame = decode(encode(practice_frame_at(index)))
                motion.feed(frame)
                for gesture in recognizer.feed(frame.millis, motion):
                    binding = book.current.binding(gesture)
                    if binding.action == "next":
                        book.cycle()
                    if binding.action == "key":
                        mapped.append(binding.key)
                        exercise.feed(binding.key, frame.millis / 1000)
            self.assertEqual(tuple(mapped), PRACTICE_KEYS)
            self.assertEqual(book.current.id, "desktop")
            self.assertEqual(exercise.errors, 0)
            self.assertAlmostEqual(exercise.duration, 3.6)

    def test_sound_is_only_optional_confirmation(self):
        recognizer = FingerGestures()
        zero = [0] * 5
        self.assertEqual(recognizer.sample(0, zero, zero, zero, True, True), ())
        angle, angular, impulse = [5, 0, 24, 0, 0], [190, 0, 355, 0, 0], [0, 0, 3, 0, 0]
        self.assertEqual(recognizer.sample(20, angle, angular, impulse, True, False), ())
        self.assertEqual(recognizer.sample(40, angle, zero, zero, True, True), ("snap",))
        self.assertEqual(recognizer.sample(60, angle, angular, impulse, True, True), ())
        recognizer.reset()
        self.assertEqual(recognizer.sample(80, angle, angular, impulse, False, True), ())
        self.assertEqual(recognizer.sample(100, angle, angular, impulse, True, None), ("snap",))

    def test_transient_rejects_constant_sound(self):
        transient = Transients()
        transient.feed([12000] * 480, 1)
        self.assertFalse(transient.near(1))
        transient.feed([0] * 240 + [20000] + [0] * 239, 2)
        self.assertTrue(transient.near(2.07))
        self.assertFalse(transient.near(2.2))

    def test_training_restarts_after_wrong_key(self):
        training = Training()
        training.feed("W", 1)
        training.feed("D", 1.5)
        self.assertEqual((training.errors, training.progress, training.start), (1, 0, None))


class KeyboardTests(unittest.TestCase):
    def test_scan_codes_held_and_released_including_extended_keys(self):
        events = []

        class FakeUser32:
            def SendInput(self, _count, pointer, size):
                self.size = size
                event = ctypes.cast(pointer, ctypes.POINTER(Input)).contents
                events.append((event.type, event.keyboard.scan, event.keyboard.flags))
                return 1

        output = WindowsMouse()
        output.api = FakeUser32()
        output.tap("W", 1.0)
        output.flush_keys(1.02)
        self.assertEqual(events, [(1, KEYS["W"], KEY_SCAN)])
        output.tap("Left", 1.03)
        output.flush_keys(1.05)
        self.assertEqual(list(output.held), ["Left"])
        output.flush_keys()
        self.assertEqual(events, [
            (1, KEYS["W"], KEY_SCAN), (1, KEYS["Left"] & 0xFF, KEY_SCAN | KEY_EXTENDED),
            (1, KEYS["W"], KEY_SCAN | KEY_UP),
            (1, KEYS["Left"] & 0xFF, KEY_SCAN | KEY_EXTENDED | KEY_UP),
        ])
        self.assertEqual(output.held, {})
