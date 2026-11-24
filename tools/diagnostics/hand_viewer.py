"""Live 3D view of the hand using the AirGloveCheck USB serial stream."""

import argparse
import math
import queue
import re
import threading
import time
import tkinter as tk

import serial
from serial.tools import list_ports


NAMES = ("Кисть", "Большой", "Указательный", "Средний", "Безымянный", "Мизинец")
COLORS = ("#4ab6bc", "#f7b76c", "#83bbfa", "#63dac8", "#bdabf7", "#efa6c4")
BACKGROUND = "#101923"
PANEL = "#182532"
TEXT = "#eef5fa"
MUTED = "#9cb0c1"
UP = (0, 0, 1)
POSE_TIMEOUT = 1.8
DEFAULT_CAMERA = (-0.22, 1.13, 1.0)
SAMPLE = re.compile(
    r"CH([0-5])\s+\w+\s+ACC=\((-?\d+),(-?\d+),(-?\d+)\)"
    r"\s+GYR=\(-?\d+,-?\d+,-?\d+\)"
    r"\s+MAG=\((-?\d+),(-?\d+),(-?\d+)\)"
)
FINGERS = (
    ((-0.64, -0.02, -0.04), -0.85, (0.50, 0.39), 0.18),
    ((-0.48, 0.68, 0), -0.10, (0.47, 0.33, 0.27), 0.15),
    ((-0.14, 0.75, 0), 0, (0.54, 0.39, 0.28), 0.157),
    ((0.22, 0.71, 0), 0.10, (0.49, 0.36, 0.26), 0.145),
    ((0.54, 0.57, 0), 0.24, (0.39, 0.26, 0.23), 0.13),
)


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def scale(vector, factor):
    return tuple(value * factor for value in vector)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    ax, ay, az = a
    bx, by, bz = b
    return ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx


def unit(vector):
    length = math.sqrt(dot(vector, vector))
    return scale(vector, 1 / length) if length > 1e-8 else None


def transpose(matrix):
    return tuple(zip(*matrix))


def transform(matrix, vector):
    return tuple(dot(row, vector) for row in matrix)


def parse_sample(line):
    match = SAMPLE.fullmatch(line)
    if match is None:
        return None
    channel, ax, ay, az, mx, my, mz = map(int, match.groups())
    return channel, (ax, ay, az), (mx, my, mz)


def sensor_frame(accel, magnetic):
    up = unit(accel)
    if up is None or magnetic is None:
        return None
    east = unit(cross(up, magnetic))
    return (cross(east, up), east, up) if east is not None else None


def hand_basis(forward):
    return transpose((cross(forward, UP), forward, UP))


def relative_pose(current, reference, basis):
    to_sensor = transpose(reference)
    to_local = transpose(basis)
    return transpose(tuple(
        transform(to_local, transform(current, transform(to_sensor, axis)))
        for axis in transpose(basis)
    ))


def serial_reader(port_name, events, stop, rescan):
    try:
        with serial.Serial(port_name, 115200, timeout=0.15, write_timeout=1) as port:
            events.put(("open", port_name))
            pending = b""
            while not stop.is_set():
                if rescan.is_set():
                    rescan.clear()
                    port.write(b"r")
                pending += port.read_until()
                if not pending.endswith(b"\n"):
                    if len(pending) > 1024:
                        pending = b""
                    continue
                line = pending.decode("ascii", errors="replace").strip()
                pending = b""
                sample = parse_sample(line)
                if sample is not None:
                    events.put(("sample", sample))
                elif line.startswith(("OK TCA9548A", "FAIL TCA9548A", "FAIL I2C init", "Configured:")):
                    events.put(("diagnostic", line))
    except (OSError, serial.SerialException) as error:
        if not stop.is_set():
            events.put(("error", str(error)))


class Viewer:
    def __init__(self, root, port, demo):
        self.root = root
        self.demo = demo
        self.frames = {}
        self.magnetic = {}
        self.times = {}
        self.reference = {}
        self.basis = hand_basis((1, 0, 0))
        self.events = queue.SimpleQueue()
        self.stop = threading.Event()
        self.rescan = threading.Event()
        self.yaw, self.pitch, self.zoom = DEFAULT_CAMERA
        self.drag_point = None
        self.hand_side = tk.BooleanVar(value=False)
        self.port = tk.StringVar(value=port)
        self.status = tk.StringVar()
        self.hint = tk.StringVar(value="Положите кисть тыльной стороной вверх, выпрямите пальцы и нажмите «Нулевая поза».")
        self.total = tk.StringVar(value="0 / 6 онлайн")
        self.root.title("AirGlove — 3D‑просмотрщик")
        self.root.configure(bg=BACKGROUND)
        self.root.geometry("1100x720")
        self.root.minsize(890, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self.reset_camera())
        self.worker = None
        self.build_ui()
        if demo:
            self.status.set("Демонстрация движения")
            self.hint.set("Мышью вращайте камеру, колесом меняйте масштаб.")
        else:
            self.connect()
        self.tick()

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        header = tk.Frame(self.root, bg=BACKGROUND)
        header.grid(row=0, columnspan=2, sticky="ew", padx=22, pady=(17, 15))
        tk.Label(header, text="AirGlove", font=("Segoe UI", 25, "bold"), bg=BACKGROUND, fg=TEXT).pack(side="left")
        tk.Label(header, textvariable=self.status, font=("Segoe UI", 11), bg=BACKGROUND, fg=MUTED).pack(side="right")
        self.canvas = tk.Canvas(self.root, bg="#121f2b", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=(22, 12))
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Double-Button-1>", lambda _event: self.reset_camera())

        panel = tk.Frame(self.root, bg=PANEL, width=248, padx=16, pady=14)
        panel.grid(row=1, column=1, sticky="nsew", padx=(0, 22))
        panel.grid_propagate(False)
        panel.columnconfigure(0, weight=1)
        tk.Label(panel, textvariable=self.total, font=("Segoe UI", 15, "bold"), bg=PANEL, fg=TEXT).grid(row=0, sticky="w")
        self.indicators = []
        for channel, name in enumerate(NAMES):
            row = tk.Label(panel, font=("Segoe UI", 11), bg=PANEL, fg=MUTED, anchor="w")
            row.grid(row=channel + 1, sticky="ew", pady=(6, 0))
            self.indicators.append(row)
        tk.Frame(panel, bg="#304454", height=1).grid(row=7, sticky="ew", pady=15)
        self.button(panel, "Нулевая поза", self.calibrate, 8)
        self.button(panel, "Задать направление кисти", self.align_heading, 9)
        tk.Checkbutton(
            panel, text="Левая рука", variable=self.hand_side, bg=PANEL, fg=TEXT,
            activebackground=PANEL, activeforeground=TEXT, selectcolor="#293c4c",
            font=("Segoe UI", 10), highlightthickness=0,
        ).grid(row=10, sticky="w", pady=4)
        if not self.demo:
            connection = tk.Frame(panel, bg=PANEL)
            connection.grid(row=11, sticky="ew", pady=(8, 0))
            entry = tk.Entry(connection, textvariable=self.port, width=8, bg="#233747", fg=TEXT,
                             relief="flat", insertbackground=TEXT, font=("Consolas", 11))
            entry.pack(side="left", ipady=5)
            entry.bind("<Return>", lambda _event: self.connect())
            tk.Button(connection, text="Подключить", command=self.connect, bg="#2b4859", fg=TEXT,
                      activebackground="#3b6378", activeforeground=TEXT, relief="flat",
                      cursor="hand2", font=("Segoe UI", 10)).pack(side="right", ipadx=6, ipady=3)
            self.button(panel, "Опросить датчики заново", self.rescan.set, 12)

        footer = tk.Frame(self.root, bg=BACKGROUND)
        footer.grid(row=2, columnspan=2, sticky="ew", padx=22, pady=(11, 12))
        tk.Label(footer, textvariable=self.hint, bg=BACKGROUND, fg=TEXT, font=("Segoe UI", 10),
                 wraplength=670, justify="left").pack(side="left")
        tk.Label(footer, text="Мышь · обзор    Колесо · масштаб", bg=BACKGROUND, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right")

    def button(self, parent, label, action, row):
        tk.Button(parent, text=label, command=action, bg="#2b4859", fg=TEXT, relief="flat",
                  activebackground="#3b6378", activeforeground=TEXT, disabledforeground=MUTED,
                  state="disabled" if self.demo else "normal",
                  cursor="hand2", font=("Segoe UI", 10)).grid(row=row, sticky="ew", pady=(0, 6), ipady=4)

    def connect(self):
        port = self.port.get().strip().upper()
        if not port:
            self.status.set("Укажите порт, например COM5")
            return
        if self.worker is not None and self.worker.is_alive():
            self.stop.set()
            self.worker.join(0.35)
            if self.worker.is_alive():
                self.status.set("Подождите, пока закроется предыдущий порт")
                return
        self.frames.clear()
        self.magnetic.clear()
        self.times.clear()
        self.reference.clear()
        self.events = queue.SimpleQueue()
        self.stop = threading.Event()
        self.rescan.clear()
        self.status.set(f"Подключение к {port}…")
        self.worker = threading.Thread(target=serial_reader,
                                       args=(port, self.events, self.stop, self.rescan), daemon=True)
        self.worker.start()
        # A USB serial open can restart the controller. Wait for its initial scan.
        worker = self.worker
        self.root.after(1500, lambda: self.rescan.set() if self.worker is worker else None)

    def close(self):
        self.stop.set()
        self.root.destroy()

    def online(self, channel):
        return self.demo or time.monotonic() - self.times.get(channel, 0) < POSE_TIMEOUT

    def calibrate(self):
        if not self.online(0) or 0 not in self.frames:
            self.hint.set("Для калибровки нужен CH0 с рабочим акселерометром и магнитометром.")
            return
        self.reference = {channel: frame for channel, frame in self.frames.items() if self.online(channel)}
        self.basis = hand_basis((1, 0, 0))
        self.hint.set("Приподнимите выпрямленную кисть на 25–45°, не сдвигая запястье. Подержите и нажмите «Задать направление кисти».")

    def align_heading(self):
        if 0 not in self.reference or not self.online(0):
            self.hint.set("Сначала задайте нулевую позу и убедитесь, что CH0 передаёт данные.")
            return
        forward_x, forward_y, _ = transform(self.reference[0], self.frames[0][2])
        if math.hypot(forward_x, forward_y) < 0.20:
            self.hint.set("Приподнимите кисть примерно на 25–45°, подержите её и нажмите кнопку ещё раз.")
            return
        self.basis = hand_basis(unit((forward_x, forward_y, 0)))
        self.hint.set("Калибровка готова. При подключении нового датчика повторите её.")

    def tick(self):
        while not self.events.empty():
            kind, value = self.events.get()
            if kind == "open":
                self.status.set(f"{value} · 115200 бод")
                self.hint.set("Положите кисть тыльной стороной вверх, выпрямите пальцы и нажмите «Нулевая поза».")
            elif kind == "error":
                self.status.set("Порт недоступен")
                self.hint.set(f"{value}. Закройте Serial Monitor и повторите подключение.")
            elif kind == "diagnostic":
                self.status.set(f"{self.port.get()} · {value.split('.')[0]}")
            elif kind == "sample":
                channel, accel, magnetic = value
                self.times[channel] = time.monotonic()
                if dot(magnetic, magnetic) > 0:
                    previous = self.magnetic.get(channel, magnetic)
                    self.magnetic[channel] = add(scale(previous, 0.55), scale(magnetic, 0.45))
                frame = sensor_frame(accel, self.magnetic.get(channel))
                if frame is not None:
                    self.frames[channel] = frame
        count = sum(self.online(channel) for channel in range(len(NAMES)))
        self.total.set("6 датчиков · демо" if self.demo else f"{count} / 6 онлайн")
        for channel, (name, indicator) in enumerate(zip(NAMES, self.indicators)):
            active = self.online(channel)
            state = "данные" if active else "нет данных"
            if self.demo:
                state = "демо"
            elif self.reference and active and channel not in self.reference:
                state = "нужна калибр."
            indicator.configure(text=f"●  {name}  ·  {state}", fg=COLORS[channel] if active else MUTED)
        self.draw()
        self.root.after(60, self.tick)

    def start_drag(self, event):
        self.drag_point = (event.x, event.y)

    def drag(self, event):
        x, y = self.drag_point
        self.yaw -= (event.x - x) * 0.012
        self.pitch = max(-1.5, min(1.5, self.pitch - (event.y - y) * 0.012))
        self.start_drag(event)

    def wheel(self, event):
        self.zoom = max(0.55, min(1.8, self.zoom * (1.12 if event.delta > 0 else 1 / 1.12)))

    def reset_camera(self):
        self.yaw, self.pitch, self.zoom = DEFAULT_CAMERA

    def draw(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        size = min(width, height) * 0.25 * self.zoom
        right = (math.cos(self.yaw), math.sin(self.yaw), 0)
        forward = (-right[1], right[0], 0)
        up = add(scale(forward, math.sin(self.pitch)), scale(UP, math.cos(self.pitch)))
        depth = cross(right, up)

        def project(point):
            point = add(point, (0, -0.43, 0))
            factor = 6 / (6 - dot(point, depth))
            return (width * 0.49 + size * factor * dot(point, right),
                    height * 0.56 - size * factor * dot(point, up))

        for index in range(-5, 6):
            t = index * 0.40
            canvas.create_line(*project((t, -2, -1.05)), *project((t, 2, -1.05)), fill="#263849")
            canvas.create_line(*project((-2, t, -1.05)), *project((2, t, -1.05)), fill="#263849")

        faces = []
        light = unit((-0.45, 0.25, 1))

        def face(points, color):
            normal = unit(cross(add(points[1], scale(points[0], -1)), add(points[2], scale(points[0], -1))))
            if normal is None or dot(normal, depth) <= 0:
                return
            shade = 0.65 + 0.35 * max(0, dot(normal, light))
            fill = "#" + "".join(f"{int(int(color[i:i+2], 16) * shade):02x}" for i in (1, 3, 5))
            faces.append((sum(dot(p, depth) for p in points) / len(points), points, fill))

        identity = ((1, 0, 0), (0, 1, 0), UP)
        poses = {
            channel: relative_pose(self.frames[channel], reference, self.basis)
            for channel, reference in self.reference.items() if self.online(channel)
        }
        palm = poses.get(0, identity)
        t = time.monotonic()
        if self.demo:
            angle = 0.63 * math.sin(t * 0.8)
            palm = ((1, 0, 0), (0, math.cos(angle), -math.sin(angle)), (0, math.sin(angle), math.cos(angle)))
        side = -1 if self.hand_side.get() else 1

        def hand_point(point):
            x, y, z = point
            return transform(palm, (side * x, y, z))

        def hand_face(points, color):
            points = tuple(map(hand_point, points))
            face(points if side == 1 else points[::-1], color)

        def tube(start, end, r1, r2, color, height_ratio=1):
            direction = unit(add(end, scale(start, -1)))
            helper = UP if abs(dot(direction, UP)) < 0.92 else (1, 0, 0)
            across = unit(cross(direction, helper))
            top = cross(direction, across)
            angles = [i * math.tau / 10 for i in range(10)]
            ring = [add(scale(across, math.cos(a)), scale(top, height_ratio * math.sin(a))) for a in angles]
            lower = [add(start, scale(v, r1)) for v in ring]
            upper = [add(end, scale(v, r2)) for v in ring]
            for i, j in zip(range(10), (*range(1, 10), 0)):
                hand_face((lower[i], lower[j], upper[j], upper[i]), color)
            hand_face(tuple(lower[::-1]), color)
            hand_face(tuple(upper), color)

        outline = ((-0.38, -0.56), (0.39, -0.60), (0.62, -0.30), (0.69, 0.39),
                   (0.58, 0.64), (0.22, 0.77), (-0.19, 0.79), (-0.55, 0.70),
                   (-0.69, 0.42), (-0.74, 0.05), (-0.57, -0.27))
        top = [(x, y, 0.14) for x, y in outline]
        bottom = [(x * 0.91, y, -0.13) for x, y in outline]
        hand_face(tuple(top), "#4ab6bc" if self.online(0) else "#546979")
        hand_face(tuple(bottom[::-1]), "#368a94")
        for i in range(len(top)):
            j = (i + 1) % len(top)
            hand_face((bottom[i], bottom[j], top[j], top[i]), "#428f99")
        tube((0, -0.90, 0), (0, -0.51, 0), 0.29, 0.36, "#41949f", height_ratio=0.52)

        for channel, (base, spread, lengths, radius) in enumerate(FINGERS, 1):
            neutral = (math.sin(spread), math.cos(spread), 0)
            if self.demo:
                flex = 0.74 + 0.64 * math.sin(t * 1.55 - channel * 0.50)
            elif 0 in poses and channel in poses:
                reflected = (side * neutral[0], neutral[1], neutral[2])
                x, y, z = transform(transpose(palm), transform(poses[channel], reflected))
                target = (side * x, y, z)
                along = dot(neutral, target)
                lateral = dot((neutral[1], -neutral[0], 0), target)
                flex = math.atan2(-z, along)
                if along < 0 and flex < -math.pi / 2:
                    flex += math.tau
                flex = max(-0.65, min(2.85, flex))
                spread += max(-0.65, min(0.65, math.atan2(lateral, math.hypot(along, z))))
            else:
                flex = 0
            weights = (0.60, 1.0) if channel == 1 else (0.44, 0.79, 1.0)
            color = COLORS[channel] if self.online(channel) else "#546979"
            point = base
            for index, (length, weight) in enumerate(zip(lengths, weights)):
                angle = flex * weight
                direction = (math.sin(spread) * math.cos(angle), math.cos(spread) * math.cos(angle), -math.sin(angle))
                end = add(point, scale(direction, length))
                thickness = radius * (1 - 0.15 * index)
                tube(add(point, scale(direction, -0.035)), end, thickness,
                     thickness * (0.72 if index == len(lengths) - 1 else 0.88), color)
                point = end

        for _, points, fill in sorted(faces, key=lambda item: item[0]):
            canvas.create_polygon(*(coordinate for point in points for coordinate in project(point)), fill=fill)
        if not self.reference and not self.demo:
            canvas.create_text(18, 19, text="Ожидание калибровки", anchor="nw", fill=MUTED, font=("Segoe UI", 10))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="USB serial port, e.g. COM5")
    parser.add_argument("--demo", action="store_true", help="show simulated motion without a device")
    options = parser.parse_args()
    port = options.port
    if port is None and not options.demo:
        port = next((p.device for p in list_ports.comports() if (p.vid, p.pid) == (0x303A, 0x1001)), "")
    root = tk.Tk()
    Viewer(root, port or "", options.demo)
    root.mainloop()


if __name__ == "__main__":
    main()
