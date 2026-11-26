"""AirGlove desktop dashboard."""

from collections import deque
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk

from . import sources
from .audio import Microphone
from .gestures import FingerGestures
from .motion import Action, Motion
from .mouse import WindowsMouse
from .panels import ProfilePanel, TrainingPanel
from .profiles import GESTURES, ProfileBook, defaults
from .protocol import ALL_CHANNELS, BATTERY_LOW, BATTERY_UNKNOWN, CALIBRATING, serial_line
from .simulation import SECTIONS, phase
from .training import Training
from .visuals import ACCENT, BG, BORDER, COLORS, MUTED, PANEL, PLOT, SURFACE, TEXT, WARM, CursorScene, HandScene

NAMES = ("Кисть", "Большой", "Указательный", "Средний", "Безымянный", "Мизинец")
POLL_MS = 8
DRAW_INTERVAL = 1 / 30
STATUS_INTERVAL = 0.10
CALIBRATION = {
    "idle": "Выпрямите пальцы и нажмите «Калибровка».",
    "collecting": "Держите кисть горизонтально, пальцы прямо. Собираю данные…",
    "failed": "Калибровка не удалась. Проверьте CH0 и повторите с неподвижной кистью.",
    "partial": "Часть каналов без калибровки. Повторите после восстановления датчиков.",
    "ready": "Поза откалибрована.",
}


class Dashboard:
    def __init__(self, root, port=None, address=None, profile_path=None):
        self.root = root
        self.address = address
        self.stop = threading.Event()
        self.inbox = queue.Queue(maxsize=256)
        self.motion = Motion()
        self.mouse = WindowsMouse()
        self.profiles = ProfileBook(profile_path)
        self.training = Training()
        self.microphone = Microphone()
        self.mic_enabled = tk.BooleanVar(value=False)
        self.recording = None
        self.record_count = 0
        self.source = "demo"
        self.practice_demo = False
        self.page = "monitor"
        self.path = None
        self.connection = tk.StringVar()
        self.metrics = tk.StringVar()
        self.battery = tk.StringVar()
        self.pose_text = tk.StringVar()
        self.profile_text = tk.StringVar(value=self.profiles.current.name)
        self.last_gesture = tk.StringVar()
        self.message = tk.StringVar()
        self.calibration = tk.StringVar()
        self.port = tk.StringVar(value=port or "")
        self.sensitivity = tk.DoubleVar(value=1)
        self.first_tick = True
        self.tick_callback = None
        self.next_draw = self.next_status = 0
        self.armed = False
        self.stream_ended = False
        self.reset_stream()
        self.build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self.disarm())

    def reset_stream(self):
        self.motion = Motion()
        self.fingers = FingerGestures()
        self.moving_at = None
        self.latest = None
        self.received = deque()
        self.missing = 0
        self.count = 0
        self.last_received = 0
        self.cursor = [0.5, 0.5]
        self.wheel = 0
        self.activities = deque(maxlen=4)
        self.activity_at = 0
        self.last_gesture.set("")

    def label(self, parent, value="", *, variable=None, color=TEXT, bg=PANEL, size=11, bold=False):
        return tk.Label(parent, text=value, textvariable=variable, bg=bg, fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"), anchor="w")

    def build(self):
        self.root.title("AirGlove")
        self.root.configure(bg=BG)
        self.root.geometry("1160x760")
        self.root.minsize(900, 690)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TButton", background=SURFACE, foreground=TEXT, borderwidth=1,
                        bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE,
                        focuscolor=ACCENT, font=("Segoe UI", 10), padding=(12, 6))
        style.map("TButton", background=[("disabled", PANEL), ("active", "#42334f")],
                  foreground=[("disabled", MUTED)])
        style.configure("Selected.TButton", background="#49304f", foreground=ACCENT,
                        bordercolor="#694674", lightcolor="#49304f", darkcolor="#49304f")
        style.configure("Primary.TButton", background=ACCENT, foreground="#24182b",
                        bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT, font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("disabled", SURFACE), ("active", "#ffdaff")],
                  foreground=[("disabled", MUTED), ("!disabled", "#24182b")],
                  bordercolor=[("disabled", BORDER)])
        style.configure("Compact.TButton", font=("Segoe UI", 9), padding=(7, 1))
        style.configure("TScale", background=ACCENT, troughcolor=BORDER, bordercolor=PANEL,
                        lightcolor=ACCENT, darkcolor=ACCENT)
        for field in ("TEntry", "TCombobox"):
            style.configure(field, fieldbackground=PLOT, foreground=TEXT, insertcolor=TEXT, padding=4,
                            bordercolor=BORDER, lightcolor=PLOT, darkcolor=PLOT,
                            selectbackground="#49304f", selectforeground=TEXT)
        style.configure("TCombobox", background=SURFACE, arrowcolor=ACCENT)
        style.configure("Compact.TCombobox", padding=(4, 1))
        style.map("TCombobox", fieldbackground=[("readonly", PLOT), ("disabled", PANEL)],
                  foreground=[("disabled", MUTED), ("readonly", TEXT)],
                  bordercolor=[("focus", ACCENT), ("!focus", BORDER)],
                  lightcolor=[("focus", PLOT), ("!focus", PLOT)], darkcolor=[("focus", PLOT), ("!focus", PLOT)])
        self.root.option_add("*TCombobox*Listbox.background", SURFACE)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#49304f")
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

        header = tk.Frame(self.root, bg=BG)
        header.grid(row=0, sticky="ew", padx=22, pady=(12, 10))
        self.label(header, "◆", bg=BG, size=16, color=WARM).pack(side="left", padx=(0, 8))
        self.label(header, "AirGlove", bg=BG, size=24, bold=True).pack(side="left")
        nav = tk.Frame(header, bg=BG)
        nav.pack(side="left", padx=20)
        self.page_buttons = {}
        for name, title in (("monitor", "Управление"), ("profiles", "Профили"), ("training", "Тренировка")):
            button = ttk.Button(nav, text=title, command=lambda target=name: self.show_page(target))
            button.pack(side="left", padx=(0, 5))
            self.page_buttons[name] = button
        status = self.label(header, variable=self.connection, bg=BG, color=ACCENT, size=10, bold=True)
        status.configure(wraplength=250, justify="right")
        status.pack(side="right")

        toolbar = tk.Frame(self.root, bg=PANEL, padx=10, pady=8)
        toolbar.grid(row=1, sticky="ew", padx=22, pady=(0, 12))
        self.label(toolbar, "Источник", color=MUTED, size=9).pack(side="left", padx=(2, 9))
        self.source_buttons = {}
        for value, label in (("demo", "Симулятор"), ("bluetooth", "Bluetooth"),
                             ("usb", "USB"), ("replay", "Повтор записи")):
            button = ttk.Button(toolbar, text=label, command=lambda mode=value: self.select(mode))
            button.pack(side="left", padx=(0, 5))
            self.source_buttons[value] = button
        port = ttk.Entry(toolbar, textvariable=self.port, width=8)
        port.pack(side="left", padx=(7, 5))
        port.bind("<Return>", lambda _event: self.select("usb"))
        self.label(toolbar, "COM (необязательно)", color=MUTED, size=9).pack(side="left")
        self.record_button = ttk.Button(toolbar, text="●  Запись", command=self.toggle_record)
        self.record_button.pack(side="right")

        surface = tk.Frame(self.root, bg=BG)
        surface.grid(row=2, sticky="nsew", padx=22)
        surface.columnconfigure(0, weight=1)
        surface.rowconfigure(0, weight=1)
        content = tk.Frame(surface, bg=BG)
        content.columnconfigure(0, weight=3, minsize=430)
        content.columnconfigure(1, weight=2, minsize=325)
        content.rowconfigure(0, weight=1)
        visual = tk.Frame(content, bg=PANEL, padx=15, pady=13)
        visual.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        visual.columnconfigure(0, weight=1)
        visual.rowconfigure(1, weight=1)
        self.label(visual, "Движение кисти", size=17, bold=True).grid(row=0, sticky="w", pady=(0, 9))
        self.label(visual, variable=self.metrics, color=ACCENT, size=10).grid(row=0, sticky="e")
        self.hand_scene = HandScene(visual)
        self.hand = self.hand_scene.canvas
        self.hand.grid(row=1, sticky="nsew")
        self.label(visual, variable=self.pose_text, color=MUTED, size=10).grid(row=2, sticky="w", pady=(8, 0))

        sidebar = tk.Frame(content, bg=PANEL, padx=15, pady=13)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        profile_row = tk.Frame(sidebar, bg=PANEL)
        profile_row.grid(row=0, sticky="ew", pady=(0, 7))
        self.label(profile_row, "Профиль", size=13, bold=True).pack(side="left", padx=(0, 10))
        self.profile_picker = ttk.Combobox(profile_row, state="readonly", textvariable=self.profile_text, width=17)
        self.profile_picker.pack(side="left", fill="x", expand=True)
        self.profile_picker.bind("<<ComboboxSelected>>", self.pick_profile)
        self.mouse_button = ttk.Button(sidebar, style="Primary.TButton", command=self.toggle_mouse)
        self.mouse_button.grid(row=1, sticky="ew", pady=(0, 8))
        self.cursor_scene = CursorScene(sidebar)
        self.preview = self.cursor_scene.canvas
        self.preview.grid(row=2, sticky="ew")
        self.activity = self.label(sidebar, color=ACCENT, size=10)
        self.activity.grid(row=3, sticky="w", pady=(5, 0))
        sensitivity = tk.Frame(sidebar, bg=PANEL)
        sensitivity.grid(row=4, sticky="ew", pady=(3, 10))
        self.label(sensitivity, "Чувствительность", size=10).pack(side="left", padx=(0, 8))
        ttk.Scale(sensitivity, from_=0.25, to=2.5, variable=self.sensitivity).pack(side="left", fill="x", expand=True)
        tk.Frame(sidebar, bg=BORDER, height=1).grid(row=5, sticky="ew", pady=(0, 7))
        self.label(sidebar, "Датчики", size=13, bold=True).grid(row=6, sticky="w")
        self.label(sidebar, variable=self.battery, color=MUTED, size=9).grid(row=6, sticky="e")
        self.channels = []
        for channel, name in enumerate(NAMES):
            row = self.label(sidebar, f"●   CH{channel}  ·  {name}", color=COLORS[channel], size=10)
            row.grid(row=7 + channel, sticky="w", pady=1)
            state = self.label(sidebar, color=MUTED, size=10)
            state.grid(row=7 + channel, sticky="e", pady=1)
            self.channels.append(state)
        calibration_tools = tk.Frame(sidebar, bg=PANEL)
        calibration_tools.grid(row=13, sticky="ew", pady=(8, 0))
        ttk.Button(calibration_tools, text="Калибровка", command=self.start_calibration).pack(
            side="left", fill="x", expand=True, padx=(0, 5))
        self.heading_button = ttk.Button(calibration_tools, text="Задать направление", command=self.align_heading)
        self.heading_button.pack(side="left", fill="x", expand=True)

        palette = (BG, PANEL, PLOT, TEXT, MUTED, ACCENT)
        self.profile_panel = ProfilePanel(surface, self, palette)
        self.training_panel = TrainingPanel(surface, self, palette)
        self.pages = {"monitor": content, "profiles": self.profile_panel.frame,
                      "training": self.training_panel.frame}
        self.show_page("monitor")
        footer = tk.Frame(self.root, bg=BG)
        footer.grid(row=3, sticky="ew", padx=22, pady=(8, 11))
        self.label(footer, variable=self.calibration, bg=BG, size=9).pack(fill="x")
        self.label(footer, variable=self.last_gesture, bg=BG, color=ACCENT, size=10).pack(fill="x")
        self.label(footer, variable=self.message, bg=BG, color=MUTED, size=9).pack(fill="x")

    def show_page(self, page):
        if page != "monitor":
            self.disarm()
        self.page = page
        for name, frame in self.pages.items():
            if name == page:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_remove()
            self.page_buttons[name].configure(style="Selected.TButton" if name == page else "TButton")
        if page == "monitor":
            self.refresh_profile_picker()
        self.next_draw = self.next_status = 0

    def refresh_profile_picker(self):
        names = []
        current = 0
        for index, profile in enumerate(self.profiles.profiles):
            name = profile.name
            while name in names:
                name += " ·"
            names.append(name)
            if profile.id == self.profiles.active:
                current = index
        self.profile_picker.configure(values=names)
        self.profile_picker.current(current)

    def pick_profile(self, _event):
        index = self.profile_picker.current()
        if index < 0:
            return
        profile = self.profiles.profiles[index]
        if profile.id == self.profiles.active:
            return
        self.disarm()
        try:
            self.profiles.activate(profile.id)
        except OSError as exc:
            self.message.set(str(exc))
        self.profile_changed()

    def profile_changed(self):
        self.release_keys()
        self.mouse.reset()
        self.moving_at = None
        self.refresh_profile_picker()
        self.profile_panel.refresh_list()
        self.training_panel.refresh()

    def select_invoker(self):
        invoker = next((p for p in self.profiles.profiles if p.id == "invoker"), None)
        if invoker is None:
            mapping = defaults()[1].bindings
            invoker = next((p for p in self.profiles.profiles if p.bindings == mapping), None)
        if invoker is None:
            self.message.set("Добавьте «Шаблон Invoker» на вкладке «Профили».")
            return False
        self.profiles.active = invoker.id
        self.profile_changed()
        return True

    def start_practice_demo(self):
        if not self.select_invoker():
            return
        self.reset_training()
        self.select("demo", practice=True)

    def reset_training(self):
        self.training.reset()
        self.training_panel.refresh()

    def update_microphone(self):
        if not self.mic_enabled.get() or self.source not in ("bluetooth", "usb"):
            self.close_microphone()
            return
        if self.microphone.stream is not None:
            return
        try:
            self.microphone.open()
        except ImportError:
            self.mic_enabled.set(False)
            self.message.set("Для микрофона установите sounddevice. Распознавание по датчикам доступно.")
        except Exception as exc:
            self.mic_enabled.set(False)
            self.message.set(f"Микрофон недоступен · {exc}")

    def close_microphone(self):
        try:
            self.microphone.close()
        except Exception as exc:
            self.message.set(f"Микрофон · {exc}")

    def select(self, mode, path=None, *, practice=False):
        if mode == "replay" and path is None:
            self.disarm()
            filename = filedialog.askopenfilename(parent=self.root, title="Открыть запись AirGlove",
                                                   filetypes=[("Записи", "*.aglog *.txt *.log"), ("Все файлы", "*.*")])
            if not filename:
                return
            path = Path(filename)
        self.disarm()
        self.finish_record()
        self.stop.set()
        self.stop = threading.Event()
        self.inbox = queue.Queue(maxsize=256)
        self.reset_stream()
        self.source = mode
        self.practice_demo = mode == "demo" and practice
        self.path = path
        self.stream_ended = False
        self.connection.set("Подготовка источника…")
        self.message.set("")
        self.update_microphone()
        for name, button in self.source_buttons.items():
            button.configure(style="Selected.TButton" if name == mode else "TButton")
        if mode in ("demo", "replay"):
            self.motion.calibrate()
        options = {
            "demo": (sources.demo, (self.practice_demo,)),
            "bluetooth": (sources.bluetooth, (self.address,)),
            "usb": (sources.usb, (self.port.get().strip(),)),
            "replay": (sources.replay, (path,)),
        }
        source, arguments = options[mode]
        threading.Thread(target=self.worker, args=(self.inbox, self.stop, source, arguments),
                         daemon=True).start()
        if self.first_tick:
            self.first_tick = False
            self.tick()

    @staticmethod
    def worker(inbox, stop, source, arguments):
        def emit(kind, payload):
            entry = (kind, payload, time.monotonic())
            try:
                inbox.put_nowait(entry)
            except queue.Full:
                try:
                    inbox.get_nowait()
                except queue.Empty:
                    pass
                inbox.put_nowait(entry)

        try:
            source(emit, stop, *arguments)
        except ImportError as exc:
            emit("ended", f"Установите зависимости из requirements.txt · {exc}")
        except OSError as exc:
            emit("ended", str(exc))

    def start_calibration(self):
        self.disarm()
        if self.stream_ended and self.source == "replay":
            self.select("replay", self.path)
        else:
            self.motion.calibrate()

    def align_heading(self):
        self.disarm()
        if self.motion.align_heading():
            self.message.set("Направление кисти задано.")
        else:
            self.message.set("Приподнимите выпрямленную кисть на 25–45° и нажмите «Задать направление».")

    def toggle_mouse(self):
        if self.armed:
            self.disarm()
        elif self.can_arm(time.monotonic()):
            self.armed = True
            self.message.set("Системный ввод включён. Esc отключает управление.")
        self.next_status = 0

    def can_arm(self, now):
        return (self.page == "monitor" and self.source in ("bluetooth", "usb") and self.mouse.api is not None
                and self.motion.ready and now - self.last_received < 0.35)

    def disarm(self):
        if self.armed:
            self.message.set("Системный ввод отключён.")
            self.next_status = 0
        self.armed = False
        self.mouse.reset()
        self.release_keys()

    def release_keys(self, now=None):
        try:
            self.mouse.flush_keys(now)
        except OSError as exc:
            self.armed = False
            self.message.set(str(exc))

    def toggle_record(self):
        if self.recording:
            self.finish_record()
            return
        self.disarm()
        filename = filedialog.asksaveasfilename(parent=self.root, title="Записать телеметрию",
                                               defaultextension=".aglog", confirmoverwrite=False,
                                               filetypes=[("Запись AirGlove", "*.aglog")])
        if not filename:
            return
        try:
            self.recording = Path(filename).open("xb")
        except FileExistsError:
            self.message.set("Этот файл уже существует. Выберите другое имя.")
            return
        except OSError as exc:
            self.message.set(f"Ошибка записи · {exc}")
            return
        self.record_count = 0
        self.record_button.configure(text="■  Остановить", style="Selected.TButton")
        self.message.set(f"Идёт запись · {Path(filename).name}")

    def finish_record(self):
        if not self.recording:
            return
        output, self.recording = self.recording, None
        try:
            output.close()
            self.message.set(f"Запись сохранена · кадров {self.record_count}")
        except OSError as exc:
            self.message.set(f"Ошибка записи · {exc}")
        self.record_button.configure(text="●  Запись", style="TButton")

    def accept_frame(self, frame, stamp, now):
        if self.recording:
            try:
                self.recording.write(serial_line(frame))
                self.record_count += 1
            except OSError as exc:
                self.finish_record()
                self.message.set(f"Ошибка записи · {exc}")
        if now - stamp >= 0.35:
            self.disarm()
            return
        if self.latest:
            gap = (frame.sequence - self.latest.sequence) & 0xFFFF
            if not gap and frame.millis == self.latest.millis:
                return
            if 1 < gap < 0x8000:
                self.missing += gap - 1
        if self.last_received and stamp - self.last_received >= 0.35:
            self.disarm()
        self.latest = frame
        self.last_received = stamp
        self.received.append(stamp)
        self.count += 1
        if self.source == "demo" and self.motion.calibration == "partial" and frame.valid == ALL_CHANNELS:
            self.motion.calibrate()
        action = self.motion.feed(frame, self.sensitivity.get())
        audio = self.microphone.detector.near(stamp) if self.microphone.stream is not None else None
        discrete = self.fingers.feed(frame.millis, self.motion, audio)
        if self.page != "profiles":
            self.route(discrete, action, stamp, now)
        if self.armed and not self.can_arm(now):
            self.disarm()

    def route(self, discrete, action, stamp, now):
        for gesture in discrete:
            self.dispatch(gesture, stamp, now)
        if "snap" in discrete:
            return
        moving = abs(action.dx) + abs(action.dy) >= 1
        if self.profiles.current.binding("motion").action == "pointer" and (action.dx or action.dy):
            self.preview_action(Action(dx=action.dx, dy=action.dy), now)
        elif moving and (self.moving_at is None or stamp - self.moving_at >= 0.18):
            self.dispatch("motion", stamp, now)
        if moving:
            self.moving_at = stamp
        if action.click:
            self.dispatch("thumb_index" if action.click == "left" else "thumb_middle", stamp, now)
        if action.wheel:
            self.dispatch("scroll_up" if action.wheel > 0 else "scroll_down", stamp, now)

    def dispatch(self, gesture, stamp, now):
        binding = self.profiles.current.binding(gesture)
        if binding.action != "none" or gesture.startswith(("tap", "lift")):
            self.last_gesture.set(f"{GESTURES[gesture]} → {binding.label()}")
        if binding.action == "next":
            self.profiles.cycle()
            self.profile_changed()
            self.add_activity(self.profiles.current.name, now)
        elif binding.action == "key":
            self.add_activity(binding.key, now, repeat=True)
            if self.page == "training":
                self.training.feed(binding.key, stamp)
                self.training_panel.refresh()
            elif self.armed and self.can_arm(now):
                try:
                    self.mouse.tap(binding.key, now)
                except OSError as exc:
                    self.disarm()
                    self.message.set(str(exc))
        elif binding.action in ("left", "right"):
            self.preview_action(Action(click=binding.action), now)
        elif binding.action in ("up", "down"):
            self.preview_action(Action(wheel=1 if binding.action == "up" else -1), now)

    def preview_action(self, action, now):
        self.cursor[0] = max(0.03, min(0.97, self.cursor[0] + action.dx / 750))
        self.cursor[1] = max(0.05, min(0.95, self.cursor[1] + action.dy / 380))
        if action.click:
            self.add_activity("ЛКМ" if action.click == "left" else "ПКМ", now)
        elif action.wheel:
            self.wheel += action.wheel
            self.add_activity("Колесо ↑" if action.wheel > 0 else "Колесо ↓", now)
        elif (abs(action.dx) + abs(action.dy)) >= 0.75:
            self.add_activity("Движение", now)
        if self.armed and self.can_arm(now):
            try:
                self.mouse.apply(action)
            except OSError as exc:
                self.disarm()
                self.message.set(str(exc))

    def add_activity(self, action, now, repeat=False):
        if repeat or not self.activities or self.activities[-1] != action or now - self.activity_at > 0.55:
            self.activities.append(action)
        self.activity_at = now

    def tick(self):
        self.tick_callback = None
        now = time.monotonic()
        if self.armed and (self.mouse.escape_pressed() or not self.can_arm(now)):
            self.disarm()
        self.release_keys(now)
        for _ in range(120):
            try:
                kind, payload, stamp = self.inbox.get_nowait()
            except queue.Empty:
                break
            if kind == "frame":
                self.accept_frame(payload, stamp, now)
            elif kind in ("status", "reset", "ended"):
                self.connection.set(payload)
                if kind == "reset":
                    self.disarm()
                    self.reset_stream()
                if kind == "ended":
                    self.stream_ended = True
                    self.disarm()
        if now >= self.next_status:
            self.update_status(now)
            self.next_status = now + STATUS_INTERVAL
        if self.page == "monitor" and now >= self.next_draw:
            if self.root.state() != "iconic":
                self.draw_hand()
                self.draw_cursor(now)
            self.next_draw = (now if now - self.next_draw > DRAW_INTERVAL else self.next_draw) + DRAW_INTERVAL
        delay = POLL_MS if not self.stream_ended and now - self.last_received < 0.35 else 24
        self.tick_callback = self.root.after(delay, self.tick)

    def update_status(self, now):
        while self.received and now - self.received[0] > 1:
            self.received.popleft()
        frame = self.latest
        fresh = now - self.last_received < 0.35
        active = frame if fresh or self.stream_ended else None
        valid = active.valid if active else 0
        interval = self.received[-1] - self.received[0] if len(self.received) > 1 else 0
        freq = round((len(self.received) - 1) / interval) if fresh and interval > 0 else 0
        metrics = f"{valid.bit_count()}/6 датчиков   ·   {freq} Гц"
        if self.missing:
            metrics += f"   ·   пропуски {self.missing}"
        self.set_text(self.metrics, metrics)
        if frame and self.source in ("usb", "bluetooth"):
            self.set_text(self.connection, ("USB" if self.source == "usb" else "BLE") +
                          (" · телеметрия" if fresh else " · ожидаю телеметрию"))
        calibration_text = CALIBRATION[self.motion.calibration]
        if frame and fresh and frame.flags & CALIBRATING:
            calibration_text = "Плата калибрует гироскопы. Держите кисть неподвижно."
        self.set_text(self.calibration, calibration_text)

        if active and active.battery_mv != BATTERY_UNKNOWN:
            voltage = f"{active.battery_mv / 1000:.2f} В"
            self.set_text(self.battery, f"Разряд · {voltage}" if active.flags & BATTERY_LOW else voltage)
        else:
            self.set_text(self.battery, "АКБ · нет измерения")
        pose = self.motion.stable
        if self.practice_demo and frame:
            pose_text = "Сценарий · тренировка Invoker"
        elif self.source == "demo" and frame:
            section = int(phase(frame.millis / 1000)[0])
            pose_text = f"Сценарий · {SECTIONS[section]}"
        elif fresh and pose is not None:
            pose_text = f"Вытянуто пальцев · {len(pose)}" if pose else "Кулак"
        else:
            pose_text = "В реальном времени" if active else "Ожидаю кадры"
        self.set_text(self.pose_text, pose_text)
        for channel, control in enumerate(self.channels):
            if valid & (1 << channel):
                extended = self.motion.extended[channel - 1] if channel else None
                text = "вытянут" if extended is True else "согнут" if extended is False else "данные"
                color = COLORS[channel]
            else:
                text, color = "нет данных", MUTED
            if control.cget("text") != text:
                control.configure(text=text, fg=color)
        if self.source in ("demo", "replay"):
            text = "Системный ввод · предпросмотр"
        elif self.armed:
            text = "Отключить системный ввод · Esc"
        else:
            text = "Включить системный ввод"
        input_state = "normal" if self.can_arm(now) else "disabled"
        if self.mouse_button.cget("text") != text or str(self.mouse_button.cget("state")) != input_state:
            self.mouse_button.configure(text=text, state=input_state)
        heading = fresh and self.motion.poses[0] is not None and self.source in ("usb", "bluetooth")
        heading_state = "normal" if heading else "disabled"
        if str(self.heading_button.cget("state")) != heading_state:
            self.heading_button.configure(state=heading_state)
        history = "   ·   ".join(self.activities)
        history = history or "Ожидание жеста"
        if self.activity.cget("text") != history:
            self.activity.configure(text=history)

    @staticmethod
    def set_text(variable, text):
        if variable.get() != text:
            variable.set(text)

    def draw_hand(self):
        fresh = time.monotonic() - self.last_received < 0.35 or self.stream_ended
        valid = self.latest.valid if self.latest and fresh else 0
        self.hand_scene.draw(self.motion, valid)

    def draw_cursor(self, now):
        clicked = bool(self.activities and self.activities[-1] in ("ЛКМ", "ПКМ")
                       and now - self.activity_at < 0.35)
        self.cursor_scene.draw(self.cursor, self.wheel, clicked)

    def close(self):
        if self.tick_callback is not None:
            self.root.after_cancel(self.tick_callback)
        self.disarm()
        self.stop.set()
        self.close_microphone()
        self.finish_record()
        self.root.destroy()
