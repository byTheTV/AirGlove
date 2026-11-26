"""Profile editor and practice views for the AirGlove dashboard."""

import tkinter as tk
from tkinter import messagebox, ttk
import time

from .mouse import KEYS
from .profiles import ACTIONS, GESTURES, Binding, Profile, defaults, new_profile, valid_actions
from .training import PRACTICE_CAPTIONS, PRACTICE_KEYS
from .visuals import BORDER, SURFACE, WARM

TRAINING_TAPS = (
    ("tap_2", "Указательный"), ("tap_3", "Средний"), ("tap_4", "Безымянный"),
    ("tap_5", "Мизинец"), ("tap_1", "Большой"), ("lift_2", "Указательный вверх"),
)


class ProfilePanel:
    def __init__(self, parent, app, palette):
        self.app, self.book = app, app.profiles
        self.bg, self.panel, self.plot, self.text, self.muted, self.accent = palette
        self.frame = tk.Frame(parent, bg=self.bg)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.editing = None
        self.profile_ids = []
        self.name = tk.StringVar()
        self.notice = tk.StringVar()

        sidebar = tk.Frame(self.frame, bg=self.panel, padx=14, pady=14)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        app.label(sidebar, "Профили", bold=True, size=16).pack(anchor="w", pady=(0, 10))
        self.listbox = tk.Listbox(sidebar, background=self.plot, foreground=self.text,
                                  selectbackground="#49304f", selectforeground=self.text,
                                  relief="flat", borderwidth=0, highlightthickness=0,
                                  exportselection=False, width=25, height=8, font=("Segoe UI", 10))
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.pick)
        for label, fn in (("Создать", self.create), ("Дублировать", self.duplicate),
                          ("Шаблон Invoker", self.add_invoker), ("Удалить", self.delete)):
            ttk.Button(sidebar, text=label, command=fn, style="Primary.TButton" if label == "Создать"
                       else "TButton").pack(fill="x", pady=(5, 0))

        editor = tk.Frame(self.frame, bg=self.panel, padx=16, pady=10)
        editor.grid(row=0, column=1, sticky="nsew")
        editor.columnconfigure(1, weight=1)
        app.label(editor, "Название").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.name).grid(row=0, column=1, columnspan=3, sticky="ew", padx=(7, 0))

        for column, heading in enumerate(("Жест", "Действие", "Клавиша")):
            app.label(editor, heading, bold=True, color=self.accent, size=9).grid(
                row=1, column=column, sticky="w", pady=(10, 4), padx=(7 if column else 0, 0))
        self.rows = {}
        for row, (gesture, label) in enumerate(GESTURES.items(), 2):
            app.label(editor, label, size=10).grid(row=row, column=0, sticky="w")
            action = ttk.Combobox(editor, state="readonly", width=22, style="Compact.TCombobox",
                                  values=[ACTIONS[value] for value in valid_actions(gesture)])
            action.grid(row=row, column=1, sticky="ew", padx=(7, 4), pady=1)
            key = ttk.Combobox(editor, width=9, values=tuple(KEYS), style="Compact.TCombobox")
            key.grid(row=row, column=2, sticky="ew", padx=(3, 0), pady=1)
            ttk.Button(editor, text="Проба", style="Compact.TButton",
                       command=lambda name=gesture: self.preview(name)).grid(row=row, column=3, padx=(6, 0))
            self.rows[gesture] = action, key
            action.bind("<<ComboboxSelected>>", lambda _event, name=gesture: self.update_key(name))
        last = 2 + len(GESTURES)
        buttons = tk.Frame(editor, bg=self.panel)
        buttons.grid(row=last, column=0, columnspan=4, sticky="ew", pady=(8, 2))
        ttk.Button(buttons, text="Сохранить", command=self.save, style="Primary.TButton").pack(side="left")
        ttk.Button(buttons, text="Активировать", command=self.activate).pack(side="left", padx=6)
        tk.Checkbutton(editor, text="Подтверждать щелчок микрофоном", variable=app.mic_enabled,
                       bg=self.panel, fg=self.text, activebackground=self.panel, activeforeground=self.text,
                       selectcolor=self.plot, highlightthickness=0, command=app.update_microphone,
                       font=("Segoe UI", 9)).grid(row=last + 1, columnspan=4, sticky="w")
        app.label(editor, variable=self.notice, color=self.muted, size=9).grid(
            row=last + 2, column=0, columnspan=4, sticky="w")
        self.load(self.book.active)
        if self.book.error:
            self.notice.set("Файл профилей не прочитан. Открыты встроенные профили.")

    def refresh_list(self):
        self.profile_ids = [profile.id for profile in self.book.profiles]
        self.listbox.delete(0, "end")
        for profile in self.book.profiles:
            prefix = "●   " if profile.id == self.book.active else "     "
            self.listbox.insert("end", prefix + profile.name)
        if self.editing in self.profile_ids:
            index = self.profile_ids.index(self.editing)
            self.listbox.selection_set(index)
            self.listbox.see(index)

    def load(self, profile_id):
        self.editing = profile_id
        profile = self.book.get(profile_id)
        self.name.set(profile.name)
        for gesture, (action, key) in self.rows.items():
            binding = profile.binding(gesture)
            action.set(ACTIONS[binding.action])
            key.set(binding.key)
            self.update_key(gesture)
        self.refresh_list()
        self.notice.set("")

    def update_key(self, gesture):
        action, key = self.rows[gesture]
        key.configure(state="readonly" if action.get() == ACTIONS["key"] else "disabled")

    def draft(self):
        bindings = {}
        for gesture, (action, key) in self.rows.items():
            selected = next(value for value, label in ACTIONS.items() if label == action.get())
            if selected != "none":
                bindings[gesture] = Binding(selected, key.get() if selected == "key" else "")
        return Profile(self.editing, self.name.get().strip(), bindings)

    def confirm_discard(self):
        changed = self.draft() != self.book.get(self.editing)
        return not changed or messagebox.askokcancel(
            "Несохранённые назначения", "Продолжить без сохранения изменений?", parent=self.frame)

    def preview(self, gesture):
        binding = self.draft().binding(gesture)
        name = "Выберите клавишу" if binding.action == "key" and not binding.key else binding.label()
        self.notice.set(f"{GESTURES[gesture]} → {name}")

    def pick(self, _event):
        selected = self.listbox.curselection()
        if selected and (profile_id := self.profile_ids[selected[0]]) != self.editing:
            if self.confirm_discard():
                self.load(profile_id)
            else:
                self.refresh_list()

    def save(self):
        try:
            self.book.save(self.draft())
        except (ValueError, OSError) as exc:
            self.notice.set(str(exc))
            return False
        if self.editing == self.book.active:
            self.app.profile_changed()
        else:
            self.refresh_list()
        recovery = f" Резервная копия · {self.book.backup.name}" if self.book.backup else ""
        self.notice.set("Профиль сохранён." + recovery)
        return True

    def activate(self):
        if self.draft() != self.book.get(self.editing) and not self.save():
            return
        try:
            self.book.activate(self.editing)
        except OSError as exc:
            self.notice.set(str(exc))
            return
        self.app.profile_changed()
        self.notice.set("Профиль активирован.")

    def save_new(self, profile):
        try:
            self.book.save(profile)
        except (ValueError, OSError) as exc:
            self.notice.set(str(exc))
        else:
            self.load(profile.id)

    def create(self):
        if self.confirm_discard():
            self.save_new(new_profile("Новый профиль"))

    def duplicate(self):
        draft = self.draft()
        self.save_new(new_profile(draft.name + " · копия", draft.bindings))

    def add_invoker(self):
        if self.confirm_discard():
            template = defaults()[1]
            self.save_new(new_profile(template.name, template.bindings))

    def delete(self):
        name = self.book.get(self.editing).name
        if not messagebox.askyesno("Удалить профиль", f"Удалить «{name}»?", parent=self.frame):
            return
        try:
            self.book.delete(self.editing)
        except (ValueError, OSError) as exc:
            self.notice.set(str(exc))
        else:
            self.load(self.book.active)
            self.app.profile_changed()


class TrainingPanel:
    def __init__(self, parent, app, palette):
        bg, panel, plot, foreground, muted, accent = palette
        self.app = app
        self.plot, self.foreground, self.muted, self.accent = plot, foreground, muted, accent
        self.frame = tk.Frame(parent, bg=panel, padx=22, pady=19)
        self.frame.columnconfigure(0, weight=1)
        app.label(self.frame, "Тренировка Invoker", size=22, bold=True).grid(row=0, sticky="w")
        self.profile_name = app.label(self.frame, color=accent, size=10)
        self.profile_name.grid(row=0, sticky="e")
        app.label(self.frame, "Соберите две комбинации сфер и примените оба слота.",
                  color=muted).grid(row=1, sticky="w", pady=(2, 16))
        self.cards = []
        keys = tk.Frame(self.frame, bg=panel)
        keys.grid(row=2, sticky="ew")
        for index, (key, caption) in enumerate(zip(PRACTICE_KEYS, PRACTICE_CAPTIONS, strict=True)):
            keys.columnconfigure(index, weight=1, uniform="sequence")
            card = tk.Frame(keys, bg=plot, padx=4, pady=10, highlightthickness=1,
                            highlightbackground=BORDER)
            card.grid(row=0, column=index, sticky="ew", padx=(0, 10 if index in (3, 7) else 4))
            symbol = app.label(card, key, bg=plot, size=20, bold=True)
            symbol.pack()
            name = app.label(card, caption, bg=plot, color=muted, size=9)
            name.pack()
            self.cards.append((card, symbol, name))
        self.result = app.label(self.frame, color=accent, size=13, bold=True)
        self.result.grid(row=3, sticky="w", pady=(15, 5))
        buttons = tk.Frame(self.frame, bg=panel)
        buttons.grid(row=4, sticky="w")
        ttk.Button(buttons, text="Демо прокаста", command=app.start_practice_demo,
                   style="Primary.TButton").pack(side="left")
        ttk.Button(buttons, text="Начать заново", command=app.reset_training).pack(side="left", padx=6)
        ttk.Button(buttons, text="Выбрать Invoker", command=app.select_invoker).pack(side="left")
        tk.Frame(self.frame, bg=BORDER, height=1).grid(row=5, sticky="ew", pady=(18, 10))
        app.label(self.frame, "Попробовать жест вручную", size=13, bold=True).grid(row=6, sticky="w")
        pads = tk.Frame(self.frame, bg=panel)
        pads.grid(row=7, sticky="ew", pady=(8, 0))
        self.pads = []
        for index, (gesture, name) in enumerate(TRAINING_TAPS):
            column = index % 3
            pads.columnconfigure(column, weight=1, uniform="pad")
            button = ttk.Button(pads, command=lambda value=gesture: self.try_gesture(value))
            button.grid(row=index // 3, column=column, sticky="ew", padx=(0, 7), pady=(0, 6))
            self.pads.append((gesture, name, button))
        self.refresh()

    def try_gesture(self, gesture):
        now = time.monotonic()
        self.app.dispatch(gesture, now, now)

    def refresh(self):
        training = self.app.training
        for index, (card, symbol, caption) in enumerate(self.cards):
            color = "#3e2c47" if index == training.progress else SURFACE if index < training.progress else self.plot
            card.configure(bg=color, highlightbackground=WARM if index == training.progress else BORDER)
            symbol.configure(bg=color, fg=self.accent if index < training.progress else self.foreground)
            caption.configure(bg=color)
        if training.duration is not None:
            status = f"Последовательность выполнена за {training.duration:.2f} с"
        else:
            status = f"{training.progress}/{len(PRACTICE_KEYS)} · ошибки {training.errors}"
            if training.last:
                status += f" · последнее нажатие {training.last}"
        self.result.configure(text=status)
        profile = self.app.profiles.current
        self.profile_name.configure(text=f"Активный профиль · {profile.name}")
        for gesture, name, button in self.pads:
            binding = profile.binding(gesture)
            button.configure(text=f"{name}  ·  {binding.key or '—'}",
                             state="normal" if binding.action == "key" else "disabled")
