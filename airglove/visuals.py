"""Canvas views for live telemetry. The geometry is updated in place."""

import math
import tkinter as tk

from .motion import dot

BG = "#111019"
PANEL = "#1b1925"
SURFACE = "#252235"
PLOT = "#14121f"
BORDER = "#39334b"
TEXT = "#faf3fb"
MUTED = "#bab0c6"
ACCENT = "#f4c0ff"
WARM = "#ffb186"
OFFLINE = "#6b607c"
COLORS = ("#f4c0ff", "#ffba86", "#8bdcf7", "#a9e3ac", "#c5b3ff", "#f49fc5")
BASE = ((-0.58, 0.00), (-0.38, 0.44), (-0.10, 0.56), (0.18, 0.49), (0.45, 0.35))
LENGTH = (0.72, 0.97, 1.0, 0.88, 0.70)
OUTLINE = ((-0.42, -0.55), (-0.62, -0.12), (-0.57, 0.31), (-0.33, 0.53),
           (0.11, 0.58), (0.47, 0.42), (0.53, 0.12), (0.36, -0.55))


def blend(a, b, weight):
    a = tuple(bytes.fromhex(a[1:]))
    b = tuple(bytes.fromhex(b[1:]))
    return "#" + "".join(f"{round(x + (y - x) * weight):02x}" for x, y in zip(a, b))


class Scene:
    def __init__(self, parent, **options):
        self.canvas = tk.Canvas(parent, bg=PLOT, highlightthickness=0, **options)
        self.size = (0, 0)
        self.geometry = None

    def prepare(self, state):
        size = self.canvas.winfo_width(), self.canvas.winfo_height()
        if min(size) <= 1:
            return False
        if size != self.size:
            self.size = size
            self.canvas.delete("background")
            self.background(*size)
            self.canvas.tag_lower("background")
            self.geometry = None
        if self.geometry == state:
            return False
        self.geometry = state
        return True


class HandScene(Scene):
    def __init__(self, parent):
        super().__init__(parent, width=1, height=1)
        canvas = self.canvas
        self.wrist = canvas.create_line(0, 0, 0, 0, width=16, capstyle="round")
        self.palm = canvas.create_polygon(0, 0, 0, 0, 0, 0, width=2)
        self.center = canvas.create_oval(0, 0, 0, 0, width=2)
        self.fingers = []
        self.valid = None
        for _ in BASE:
            halo = canvas.create_line(0, 0, 0, 0, 0, 0, capstyle="round", joinstyle="round")
            bone = canvas.create_line(0, 0, 0, 0, 0, 0, capstyle="round", joinstyle="round")
            node = canvas.create_oval(0, 0, 0, 0, width=2)
            tip = canvas.create_oval(0, 0, 0, 0, width=2)
            self.fingers.append((halo, bone, node, tip))

    def background(self, width, height):
        canvas = self.canvas
        for y in range(0, height, 4):
            height_ratio = y / height
            tint = blend("#171321", "#2d173b", math.sin(math.pi * height_ratio) ** 2)
            canvas.create_rectangle(0, y, width, y + 4, fill=tint, outline="", tags="background")
        for row in range(15):
            positions = []
            t = row / 14
            for step in range(19):
                x = step / 18
                bend = math.sin(5.1 * x + 1.15 * t - 0.9) * (0.15 + 0.06 * t)
                y = 0.44 + 0.42 * t + bend + 0.11 * math.sin(8.7 * x - t * 1.4)
                positions.extend((width * x, height * y))
            tone = blend("#322042", "#75435d", 0.21 + 0.50 * t)
            canvas.create_line(*positions, fill=tone, smooth=True, tags="background")
        for x in range(22, width, 35):
            for y in range(24, height, 35):
                canvas.create_rectangle(x, y, x + 1, y + 1, outline="", fill="#564364", tags="background")

    def draw(self, motion, valid):
        palm = motion.poses[0] if valid else None
        forward, right = motion.forward, motion.right
        directions = tuple(motion.directions[1:]) if valid else (None,) * len(BASE)
        rotation = palm.rotation if palm is not None else None
        if not self.prepare((valid, rotation, directions, forward, right)):
            return
        canvas = self.canvas
        width, height = self.size
        scale = min(width * 0.245, height * 0.34)

        def point(x, y, z=0):
            return width / 2 + scale * x, height * 0.68 - scale * (y * 0.90 + z * 0.56)

        def orient(x, y):
            if palm is None:
                return x, y, 0
            vector = palm.direction(tuple(x * a + y * b for a, b in zip(right, forward)))
            return dot(vector, right), dot(vector, forward), vector[2]

        def oval(item, xy, radius):
            x, y = xy
            canvas.coords(item, x - radius, y - radius, x + radius, y + radius)

        canvas.coords(self.palm, *(value for x, y in OUTLINE for value in point(*orient(x, y))))
        canvas.coords(self.wrist, *point(*orient(-0.02, -0.84)), *point(*orient(-0.02, -0.53)))
        oval(self.center, point(*orient(-0.03, -0.09)), 6)
        for index, (base, length, direction, items) in enumerate(zip(BASE, LENGTH, directions, self.fingers), 1):
            halo, bone, node, tip = items
            x, y, z = orient(*base)
            vx, vy, vz = ((dot(direction, right), dot(direction, forward), direction[2])
                          if direction else orient((index - 3) * 0.30, 0.92 if index > 1 else 0.55))
            bend = max(0, -vz)
            joint = (x + vx * length * 0.46, y + length * (vy * 0.36 + bend * 0.22),
                     z + vz * length * 0.30)
            end = (x + vx * length, y + vy * length, z + vz * length * 0.67)
            joint_point, tip_point = point(*joint), point(*end)
            coordinates = (*point(x, y, z), *joint_point, *tip_point)
            canvas.coords(halo, *coordinates)
            canvas.coords(bone, *coordinates)
            oval(node, joint_point, 3.5)
            oval(tip, tip_point, 6.5)
        if self.valid != valid:
            self.valid = valid
            color = COLORS[0] if valid & 1 else OFFLINE
            canvas.itemconfigure(self.palm, fill="#392647", outline=color)
            canvas.itemconfigure(self.wrist, fill=blend(PLOT, color, 0.46))
            canvas.itemconfigure(self.center, outline=color, fill=PLOT)
            for index, (halo, bone, node, tip) in enumerate(self.fingers, 1):
                color = COLORS[index] if valid & (1 << index) else OFFLINE
                canvas.itemconfigure(halo, fill=blend(PLOT, color, 0.29), width=12)
                canvas.itemconfigure(bone, fill=color, width=4)
                canvas.itemconfigure(node, fill=PLOT, outline=color)
                canvas.itemconfigure(tip, fill=PLOT, outline=color)


class CursorScene(Scene):
    def __init__(self, parent):
        super().__init__(parent, height=104, width=1)
        self.counter = self.canvas.create_text(0, 0, anchor="ne", fill=MUTED, font=("Consolas", 10))
        self.pulse = self.canvas.create_oval(0, 0, 0, 0, outline=WARM, width=2, state="hidden")
        self.pointer = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=ACCENT, outline=PLOT)

    def background(self, width, height):
        for x in range(14, width, 18):
            for y in range(13, height, 18):
                self.canvas.create_rectangle(x, y, x + 1, y + 1, fill=BORDER, outline="", tags="background")

    def draw(self, cursor, wheel, clicked):
        if not self.prepare((tuple(cursor), wheel, clicked)):
            return
        width, height = self.size
        x, y = cursor[0] * (width - 19), cursor[1] * (height - 24)
        self.canvas.coords(self.counter, width - 10, 9)
        self.canvas.itemconfigure(self.counter, text=f"Колесо {wheel:+d}")
        self.canvas.coords(self.pulse, x - 9, y - 9, x + 21, y + 21)
        self.canvas.itemconfigure(self.pulse, state="normal" if clicked else "hidden")
        self.canvas.coords(self.pointer, x, y, x, y + 19, x + 5, y + 13, x + 11, y + 19,
                           x + 14, y + 16, x + 9, y + 11, x + 16, y + 10)
