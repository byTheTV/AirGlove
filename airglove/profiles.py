"""Editable gesture bindings stored separately from telemetry."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from .mouse import KEYS

GESTURES = {
    "tap_1": "Тап большим",
    "tap_2": "Тап указательным",
    "tap_3": "Тап средним",
    "tap_4": "Тап безымянным",
    "tap_5": "Тап мизинцем",
    "lift_2": "Тап указательным вверх",
    "snap": "Щелчок большим и средним",
    "motion": "Движение одним вытянутым пальцем",
    "scroll_up": "Взмах кистью вверх",
    "scroll_down": "Взмах кистью вниз",
    "thumb_index": "Удержание большого и указательного",
    "thumb_middle": "Удержание большого и среднего",
}
ACTIONS = {
    "none": "Без действия",
    "key": "Клавиша",
    "left": "Левый клик",
    "right": "Правый клик",
    "up": "Прокрутка вверх",
    "down": "Прокрутка вниз",
    "next": "Следующий профиль",
    "pointer": "Движение курсора",
}


@dataclass(frozen=True)
class Binding:
    action: str = "none"
    key: str = ""

    def label(self):
        return self.key if self.action == "key" else ACTIONS[self.action]


def valid_actions(gesture):
    return tuple(value for value in ACTIONS if value != "pointer" or gesture == "motion")


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    bindings: dict[str, Binding]

    def binding(self, gesture):
        return self.bindings.get(gesture, Binding())


def defaults():
    desktop = Profile("desktop", "Рабочий стол", {
        "motion": Binding("pointer"), "scroll_up": Binding("up"), "scroll_down": Binding("down"),
        "thumb_index": Binding("left"), "thumb_middle": Binding("right"), "snap": Binding("next"),
    })
    invoker = Profile("invoker", "Dota 2 · Invoker", {
        "tap_1": Binding("key", "D"), "tap_2": Binding("key", "Q"), "tap_3": Binding("key", "W"),
        "tap_4": Binding("key", "E"), "tap_5": Binding("key", "R"), "lift_2": Binding("key", "F"),
        "motion": Binding("pointer"), "thumb_index": Binding("left"), "thumb_middle": Binding("right"),
        "snap": Binding("next"),
    })
    return [desktop, invoker]


def settings_path():
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".config") / "AirGlove" / "profiles.json"


class ProfileBook:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else settings_path()
        self.profiles = defaults()
        self.preferred = self.active = self.profiles[0].id
        self.error = None
        self.backup = None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            profiles = self.parse(data)
            self.profiles = profiles
            preferred = data.get("active")
            self.preferred = self.active = (preferred if any(p.id == preferred for p in profiles)
                                            else profiles[0].id)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.error = str(exc)

    @staticmethod
    def parse(data):
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("profiles"), list):
            raise ValueError("Неизвестный формат профилей")
        profiles = []
        for item in data["profiles"]:
            if not isinstance(item, dict):
                raise ValueError("Недопустимая запись профиля")
            profile_id, name, values = item["id"], item["name"], item["bindings"]
            if not isinstance(profile_id, str) or not profile_id or not isinstance(name, str) or not name.strip():
                raise ValueError("У одного из профилей отсутствует имя или идентификатор")
            if any(p.id == profile_id for p in profiles):
                raise ValueError("Повторяется идентификатор профиля")
            if not isinstance(values, dict):
                raise ValueError(f"Недопустимые назначения профиля {name}")
            bindings = {}
            for gesture, value in values.items():
                if gesture not in GESTURES:
                    continue
                if not isinstance(value, dict):
                    raise ValueError(f"Недопустимое назначение жеста {gesture}")
                action, key = value["action"], value.get("key", "")
                if action not in valid_actions(gesture) or (action == "key" and
                                                             (not isinstance(key, str) or key not in KEYS)):
                    raise ValueError(f"Недопустимое назначение жеста {gesture}")
                if action != "none":
                    bindings[gesture] = Binding(action, key if action == "key" else "")
            profiles.append(Profile(profile_id, name, bindings))
        if not profiles:
            raise ValueError("В файле нет профилей")
        return profiles

    def get(self, profile_id):
        return next(p for p in self.profiles if p.id == profile_id)

    @property
    def current(self):
        return self.get(self.active)

    def cycle(self):
        index = next(i for i, p in enumerate(self.profiles) if p.id == self.active)
        self.active = self.profiles[(index + 1) % len(self.profiles)].id
        return self.current

    def activate(self, profile_id):
        self.get(profile_id)
        self._commit(self.profiles, profile_id)
        self.active = profile_id

    def save(self, profile):
        items = [profile if p.id == profile.id else p for p in self.profiles]
        if all(p.id != profile.id for p in self.profiles):
            items.append(profile)
        self._commit(items, self.preferred)

    def delete(self, profile_id):
        items = [p for p in self.profiles if p.id != profile_id]
        if not items:
            raise ValueError("Оставьте хотя бы один профиль")
        preferred = items[0].id if self.preferred == profile_id else self.preferred
        self._commit(items, preferred)
        if self.active == profile_id:
            self.active = preferred

    def _commit(self, items, preferred):
        payload = {
            "version": 1, "active": preferred,
            "profiles": [{"id": item.id, "name": item.name, "bindings": {
                name: {"action": value.action, "key": value.key}
                for name, value in item.bindings.items()
            }} for item in items],
        }
        self.parse(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.error is not None and self.backup is None:
            original = self.path.read_bytes()
            with tempfile.NamedTemporaryFile(prefix="profiles-backup-", suffix=".json",
                                             dir=self.path.parent, delete=False) as backup:
                backup.write(original)
                self.backup = Path(backup.name)
        staged = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             delete=False) as output:
                staged = Path(output.name)
                json.dump(payload, output, ensure_ascii=False, indent=2)
                output.write("\n")
            staged.replace(self.path)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
        self.profiles, self.preferred = items, preferred
        self.error = None


def new_profile(name, bindings=None):
    return Profile(uuid4().hex, name, dict(bindings) if bindings is not None else {"snap": Binding("next")})
