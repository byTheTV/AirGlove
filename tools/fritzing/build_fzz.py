"""Сборка Fritzing-проекта AirGlove (docs/fritzing/AirGlove.fzz).

Детали:
  * готовые детали сообщества (tools/fritzing/parts, авторы в CREDITS.md) — встраиваются в .fzz как есть:
    ESP32-C3 SuperMini, TCA9548A, TP4056 Type-C, MT3608, Li-Po 1300 мА·ч;
  * стандартные детали Fritzing (тумблер, диод Шоттки) — берутся из библиотеки самого Fritzing;
  * свои детали, которые генерирует этот скрипт: GY-BNO055 (фиолетовый CJMCU-055) и P1 — наша плата
    распределения.

Запуск: python tools/fritzing/build_fzz.py
Дальше проект открывается в Fritzing (File → Open) и правится мышкой как обычно.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARTS_DIR = Path(__file__).resolve().parent / "parts"
OUT_DIR = ROOT / "docs" / "fritzing"
FZZ = OUT_DIR / "AirGlove.fzz"
PX = 0.09  # 1 мил = 0.09 px сцены Fritzing (90 dpi)
FONT = "Droid Sans"

# ============================================================================ описание деталей


@dataclass
class PartDef:
    key: str
    mid: str                                   # moduleId
    w: float                                   # мил
    h: float
    pins: dict[str, tuple[int, float, float]]  # имя -> (номер connector, x, y) в милах
    path: str
    vendored: Path | None = None               # папка с файлами для встраивания в .fzz
    custom: "CustomPart | None" = None         # своя деталь (генерируется)
    legs: dict[str, tuple[float, float, float, float]] = field(default_factory=dict)  # px: x0, y0, dx, dy


def ext(key, folder, mid, size_px, pins_px, legs=None, path=None, dpi=90):
    """Деталь с замеренными координатами пинов (px SVG, см. measure_pins.py).

    dpi: как Fritzing переводит px этого SVG в дюймы. Для SVG из Adobe Illustrator с размерами в px
    Fritzing берёт 72 dpi, для остальных — 90.
    """
    k = 1000 / dpi  # мил на px SVG
    pins = {n: (i, x * k, y * k) for n, (i, x, y) in pins_px.items()}
    if legs:  # провод подключается к концу гибкого вывода
        for n, (x0, y0, dx, dy) in legs.items():
            i = pins[n][0]
            pins[n] = (i, (x0 + dx) * k, (y0 + dy) * k)
    return PartDef(key, mid, size_px[0] * k, size_px[1] * k, pins,
                   path or f"{mid}.fzp", PARTS_DIR / folder if folder else None, legs=legs or {})


EXT_PARTS = {
    "esp": ext("esp", "esp32c3_supermini", "esp32-c3-super-mini-tht_1", (63.8116, 86.2006), {
        # правый ряд сверху вниз: 5V G 3.3 4 3 2 1 0; левый: 5 6 7 8 9 10 20 21
        "5V": (15, 58.92, 11.89), "G": (14, 58.92, 20.89), "3.3": (13, 58.92, 29.89),
        "GPIO4": (12, 58.92, 38.89), "GPIO3": (11, 58.92, 47.89), "GPIO2": (10, 58.92, 56.89),
        "GPIO1": (9, 58.92, 65.89), "GPIO0": (8, 58.92, 74.89),
        "GPIO5": (0, 4.92, 11.85), "GPIO6": (1, 4.92, 20.89), "GPIO7": (2, 4.92, 29.89),
        "GPIO8": (3, 4.92, 38.89), "GPIO9": (4, 4.92, 47.89), "GPIO10": (5, 4.92, 56.89),
        "GPIO20": (6, 4.92, 65.89), "GPIO21": (7, 4.92, 74.89)}),
    "tca": ext("tca", "tca9548a", "adafruit_6220ddee62398d885fd79aedffc82196_1", (63.0, 108.0), {
        "VIN": (16, 4.5, 4.5), "GND": (17, 4.5, 13.5), "SDA": (18, 4.5, 22.5), "SCL": (19, 4.5, 31.5),
        "RST": (20, 4.5, 40.5), "A0": (21, 4.5, 49.5), "A1": (22, 4.5, 58.5), "A2": (23, 4.5, 67.5),
        "SD0": (24, 4.5, 76.5), "SC0": (25, 4.5, 85.5), "SD1": (26, 4.5, 94.5), "SC1": (27, 4.5, 103.5),
        "SC7": (15, 58.5, 4.5), "SD7": (14, 58.5, 13.5), "SC6": (13, 58.5, 22.5), "SD6": (12, 58.5, 31.5),
        "SC5": (11, 58.5, 40.5), "SD5": (10, 58.5, 49.5), "SC4": (9, 58.5, 58.5), "SD4": (8, 58.5, 67.5),
        "SC3": (7, 58.5, 76.5), "SD3": (6, 58.5, 85.5), "SC2": (5, 58.5, 94.5), "SD2": (4, 58.5, 103.5)}),
    "tp4056": ext("tp4056", "tp4056_typec", "TP4056_protection_TypeC", (48.2, 81.335), {
        "IN-": (0, 4.6, 8.23), "IN+": (1, 43.7, 8.23), "B-": (2, 13.5, 72.03), "B+": (3, 34.8, 72.03),
        "OUT-": (4, 4.6, 72.03), "OUT+": (5, 43.7, 72.03)}, dpi=72),
    "mt3608": ext("mt3608", "mt3608", "MT3608_Module", (127.8711, 60.5475), {
        "VIN-": (0, 116.89, 42.39), "VIN+": (1, 116.89, 18.16), "VOUT+": (2, 10.98, 18.16),
        "VOUT-": (3, 10.98, 42.39)}),
    "lipo": ext("lipo", "lipo_1300mah", "429554780853871ee7a5d41bb711aebd", (135.0, 396.0), {
        "+": (1, 67.5, 9.0), "-": (2, 76.5, 9.0)}),
    # стандартные детали Fritzing (не встраиваются)
    "switch": ext("switch", None, "1238DBDC00-toggle-switch", (33.2982, 33.8328), {
        "L1": (0, 6.56, 29.74), "COM": (1, 15.56, 29.74), "L2": (2, 24.56, 29.74)},
        path=":/resources/parts/core/basic-toggle-switch.fzp"),
    "diode": ext("diode", None, "145554CBFC44diode", (37.3487, 9.0), {"K": (0, 0, 0), "A": (1, 0, 0)},
                 legs={"K": (2.6175, 4.5375, -1.3088, 0.0), "A": (34.7312, 4.5375, 1.3088, 0.0)},
                 path=":/resources/parts/core/diode_schottky_1N5817_300mil.fzp"),
}

# ============================================================================ свои детали (SVG + FZP)


@dataclass
class Pin:
    name: str
    x: float
    y: float
    desc: str = ""
    ctype: str = "male"   # male — штырь, female — гнездо (в него вставляется модуль)


@dataclass
class CustomPart:
    key: str
    title: str
    label: str
    w: float
    h: float
    pins: list[Pin]
    art: str
    desc: str
    family: str
    buses: list[list[str]] = field(default_factory=list)
    sch_left: list[str] | None = None

    @property
    def mid(self) -> str:
        return f"AirGlove_{self.key}_v2"

    def idx(self, name: str) -> int:
        for i, p in enumerate(self.pins):
            if p.name == name:
                return i
        raise KeyError(f"{self.key}: нет пина {name}")

    def as_def(self) -> PartDef:
        pins = {p.name: (i, p.x, p.y) for i, p in enumerate(self.pins)}
        return PartDef(self.key, self.mid, self.w, self.h, pins, f"{self.mid}.fzp", custom=self)


def txt(x, y, s, size=50, color="#ffffff", anchor="middle", weight="normal", rot=None):
    tr = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{tr}>{h(s)}</text>')


def rect(x, y, w, hh, fill, stroke="none", sw=0, rx=0):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{hh}" rx="{rx}" ry="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


def circ(x, y, r, fill, stroke="none", sw=0):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def line(x1, y1, x2, y2, color, width):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>'


def smd(x, y, w, hh, body="#c8a96e"):
    """SMD-резистор/конденсатор: корпус и два вывода."""
    return (rect(x, y, w, hh, body) + rect(x, y, w * 0.22, hh, "#d9d9d9") +
            rect(x + w * 0.78, y, w * 0.22, hh, "#d9d9d9"))


def make_bno() -> CustomPart:
    """Фиолетовый GY-BNO055 / CJMCU-055: 8 пинов в ряд, S0/S1, место под кварц, крепёжные отверстия."""
    w, hh = 1050, 850
    names = ["VCC", "GND", "ATX", "LRX", "I2C", "INT", "RES", "BOOT"]
    descs = ["3,3 В", "GND", "SDA в режиме I²C", "SCL в режиме I²C", "адрес: GND=0x28, 3V3=0x29",
             "прерывание (не исп.)", "сброс (не исп.)", "загрузчик (не исп.)"]
    pins = [Pin(n, 175 + 100 * i, 780, d) for i, (n, d) in enumerate(zip(names, descs))]
    a = rect(0, 0, w, hh, "#5b2a86", "#3a1658", 8, 40)
    for cx in (95, 955):  # крепёжные отверстия с золотым кольцом
        a += circ(cx, 95, 62, "#d4a017") + circ(cx, 95, 42, "#ffffff")
    a += circ(735, 70, 22, "#d4a017") + circ(735, 70, 9, "#1a1a1a")   # отверстия под кварц
    a += circ(815, 70, 22, "#d4a017") + circ(815, 70, 9, "#1a1a1a")
    a += rect(690, 105, 170, 46, "#c9c9c9", "#7a7a7a", 3, 20) + txt(775, 140, "32.768K", 26, "#444")
    a += rect(395, 255, 260, 260, "#2b2b2b", "#111", 4, 6) + circ(420, 280, 12, "#888")  # BNO055 LGA
    a += txt(525, 395, "BNO055", 46, "#bdbdbd")
    a += rect(170, 205, 110, 60, "#1c1c1c") + txt(225, 245, "662K", 24, "#aaa")          # стабилизатор
    for x, y in ((180, 300), (180, 350), (720, 230), (720, 290), (720, 350), (300, 560), (430, 560),
                 (560, 560), (690, 560)):
        a += smd(x, y, 80, 34)
    a += rect(150, 420, 70, 42, "#d4a017") + rect(230, 420, 70, 42, "#d4a017") + txt(310, 455, "S0", 30, anchor="start")
    a += rect(150, 480, 70, 42, "#d4a017") + rect(230, 480, 70, 42, "#d4a017") + txt(310, 515, "S1", 30, anchor="start")
    a += txt(820, 455, "GY-BNO055", 44) + txt(820, 505, "CJMCU-055", 30, "#e4d2f5")
    for p in pins:
        a += txt(p.x + 12, 720, p.name, 30, rot=-90, anchor="start")
    return CustomPart("GY_BNO055", "GY-BNO055 (CJMCU-055)", "U", w, hh, pins, a,
                      "Фиолетовый модуль GY-BNO055 / CJMCU-055. ATX = SDA, LRX = SCL; перемычки S0/S1 на GND = I²C.",
                      "imu (bno055)")


P1_N = 8  # штырей в каждом ряду: ESP, TCA и 6 датчиков


def make_p1() -> CustomPart:
    """P1 — маленькая плата питания: перфоплата 10×3 отверстия (25×8 мм), ряд 3V3 и ряд GND по 8 штырей."""
    w, hh = 1000, 300
    pins: list[Pin] = []
    for i in range(P1_N):
        x = 150 + 100 * i
        pins.append(Pin(f"3V3.{i + 1}", x, 50, "шина 3V3"))
        pins.append(Pin(f"GND.{i + 1}", x, 250, "шина GND"))
    a = rect(0, 0, w, hh, "#3b7d4f", "#21482d", 6, 12)
    a += "".join(circ(50 + 100 * c, 50 + 100 * r, 14, "#c9d9cc", "#7f9c86", 4) for c in range(10) for r in range(3))
    a += line(50, 50, 950, 50, "#c0c0c0", 34) + line(50, 50, 950, 50, "#e53935", 12)
    a += line(50, 250, 950, 250, "#c0c0c0", 34) + line(50, 250, 950, 250, "#262626", 12)
    a += txt(50, 168, "3V3", 46, "#ffd0d0", anchor="start", weight="bold")
    a += txt(950, 168, "GND", 46, "#e8e8e8", anchor="end", weight="bold")
    buses = [[f"3V3.{i + 1}" for i in range(P1_N)], [f"GND.{i + 1}" for i in range(P1_N)]]
    return CustomPart("P1_Power", "P1 плата питания 3V3/GND (25×8 мм)", "P", w, hh, pins, a,
                      "Маленькая перфоплата 10×3 отверстия: верхний ряд 8 штырей — шина 3V3, нижний ряд 8 штырей — "
                      "шина GND (на обороте каждый ряд пропаян лужёным проводом). Вход — 3V3 и GND с ESP32-C3, "
                      "выходы — TCA9548A и 6 датчиков.",
                      "power distribution board", buses)


CUSTOM = {"bno": make_bno(), "p1": make_p1()}
PARTS: dict[str, PartDef] = dict(EXT_PARTS)
PARTS.update({k: v.as_def() for k, v in CUSTOM.items()})


def svg_root(w, hh, body):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.2" width="{w / 1000}in" height="{hh / 1000}in" '
            f'viewBox="0 0 {w} {hh}">\n{body}\n</svg>\n')


def bb_svg(p: CustomPart) -> str:
    pins = "".join(f'<circle id="connector{i}pin" cx="{pin.x}" cy="{pin.y}" r="36" fill="#d4a017" '
                   f'stroke="#8a6d00" stroke-width="10"/>' + circ(pin.x, pin.y, 15, "#1a1a1a")
                   for i, pin in enumerate(p.pins))
    return svg_root(p.w, p.h, f'<g id="breadboard">{p.art}{pins}</g>')


def sch_geometry(p: CustomPart):
    n = len(p.pins)
    if p.sch_left:
        left = [i for i, pin in enumerate(p.pins) if pin.name in p.sch_left]
        right = [i for i in range(n) if i not in left]
    else:
        left, right = list(range((n + 1) // 2)), list(range((n + 1) // 2, n))
    rows = max(len(left), len(right))
    bw = 1200
    pos = {i: ("L", 300 + r * 100) for r, i in enumerate(left)}
    pos.update({i: ("R", 300 + r * 100) for r, i in enumerate(right)})
    return bw + 400, 300 + rows * 100, bw, pos


def sch_svg(p: CustomPart) -> str:
    w, hh, bw, pos = sch_geometry(p)
    body = rect(200, 150, bw, hh - 200, "#ffffff", "#000000", 10) + txt(200 + bw / 2, 110, p.title, 70, "#000")
    for i, pin in enumerate(p.pins):
        side, y = pos[i]
        x1, x2, tx, anchor = (0, 200, 220, "start") if side == "L" else (w - 200, w, w - 220, "end")
        tx_term = 0 if side == "L" else w - 10
        body += f'<line id="connector{i}pin" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#555555" stroke-width="10"/>'
        body += f'<rect id="connector{i}terminal" x="{tx_term}" y="{y - 5}" width="10" height="10" fill="none"/>'
        body += txt(tx, y + 20, pin.name, 55, "#000", anchor=anchor)
    return svg_root(w, hh, f'<g id="schematic">{body}</g>')


def pcb_svg(p: CustomPart) -> str:
    silk = f'<rect x="10" y="10" width="{p.w - 20}" height="{p.h - 20}" fill="none" stroke="#ffffff" stroke-width="10"/>'
    pads = "".join(f'<circle id="connector{i}pad" cx="{pin.x}" cy="{pin.y}" r="30" fill="none" '
                   f'stroke="#F7BD13" stroke-width="20"/>' for i, pin in enumerate(p.pins))
    return svg_root(p.w, p.h, f'<g id="silkscreen">{silk}</g><g id="copper1"><g id="copper0">{pads}</g></g>')


def fzp(p: CustomPart) -> str:
    conns = "\n".join(f'''  <connector id="connector{i}" name="{h(pin.name)}" type="{pin.ctype}">
   <description>{h(pin.desc or pin.name)}</description>
   <views>
    <breadboardView><p layer="breadboard" svgId="connector{i}pin"/></breadboardView>
    <schematicView><p layer="schematic" svgId="connector{i}pin" terminalId="connector{i}terminal"/></schematicView>
    <pcbView><p layer="copper0" svgId="connector{i}pad"/><p layer="copper1" svgId="connector{i}pad"/></pcbView>
   </views>
  </connector>''' for i, pin in enumerate(p.pins))
    buses = ""
    if p.buses:
        bl = "\n".join(f'  <bus id="bus{bi}">' + "".join(f'<nodeMember connectorId="connector{p.idx(m)}"/>'
                                                         for m in members) + "</bus>"
                       for bi, members in enumerate(p.buses))
        buses = f" <buses>\n{bl}\n </buses>"
    b = p.key
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="0.9.4" moduleId="{p.mid}">
 <version>2</version>
 <author>AirGlove P3319</author>
 <title>{h(p.title)}</title>
 <label>{p.label}</label>
 <date>2026-11-15</date>
 <tags><tag>AirGlove</tag></tags>
 <properties>
  <property name="family">AirGlove {h(p.family)}</property>
  <property name="variant">{h(p.key)}</property>
 </properties>
 <description>{h(p.desc)}</description>
 <views>
  <iconView><layers image="breadboard/{b}_breadboard.svg"><layer layerId="icon"/></layers></iconView>
  <breadboardView><layers image="breadboard/{b}_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>
  <schematicView><layers image="schematic/{b}_schematic.svg"><layer layerId="schematic"/></layers></schematicView>
  <pcbView><layers image="pcb/{b}_pcb.svg"><layer layerId="silkscreen"/><layer layerId="copper0"/><layer layerId="copper1"/></layers></pcbView>
 </views>
 <connectors>
{conns}
 </connectors>
{buses}
</module>
'''


# ============================================================================ расстановка


def rotate_local(x, y, w, hh, rot):
    """Поворот точки детали вокруг её центра (как это делает Fritzing). rot: 0, 90 (по часовой), -90, 180."""
    cx, cy = w / 2, hh / 2
    if rot == 90:
        return -(y - cy) + cx, (x - cx) + cy
    if rot == -90:
        return (y - cy) + cx, -(x - cx) + cy
    if rot == 180:
        return 2 * cx - x, 2 * cy - y
    return x, y


def transform_xml(p: PartDef, rot) -> str:
    if not rot:
        return ""
    cx, cy = p.w * PX / 2, p.h * PX / 2
    m = {90: (0, 1, -1, 0, cx + cy, cy - cx), -90: (0, -1, 1, 0, cx - cy, cx + cy),
         180: (-1, 0, 0, -1, 2 * cx, 2 * cy)}[rot]
    return (f'<transform m11="{m[0]}" m12="{m[1]}" m13="0" m21="{m[2]}" m22="{m[3]}" m23="0" '
            f'm31="{m[4]:.4f}" m32="{m[5]:.4f}" m33="1"/>')


@dataclass
class Inst:
    key: str
    ref: str
    x: float
    y: float
    rot: int = 0
    caption: str = ""
    label_at: tuple[float, float] | None = None
    props: dict = field(default_factory=dict)  # свойства экземпляра (например, номинал диода)
    index: int = 0
    conns: dict = field(default_factory=dict)
    direct: dict = field(default_factory=dict)  # connector -> [(ref другой детали, её connector)]

    @property
    def part(self) -> PartDef:
        return PARTS[self.key]

    def pin(self, name):
        i, px, py = self.part.pins[name]
        rx, ry = rotate_local(px, py, self.part.w, self.part.h, self.rot)
        return i, (self.x + rx, self.y + ry)

    def bbox(self):
        p = self.part
        pts = [rotate_local(x, y, p.w, p.h, self.rot) for x, y in ((0, 0), (p.w, 0), (0, p.h), (p.w, p.h))]
        return (self.x + min(q[0] for q in pts), self.y + min(q[1] for q in pts),
                self.x + max(q[0] for q in pts), self.y + max(q[1] for q in pts))


INST: dict[str, Inst] = {}


def place(ref, key, x, y, caption="", rot=0, label_at=None):
    INST[ref] = Inst(key, ref, x, y, rot, caption, label_at)
    return INST[ref]


DIRECT: list[tuple[str, str, str, str]] = []  # прямые соединения без провода (сейчас не используются)
OX = 4000                                      # общий сдвиг схемы вправо (мил)


def P(ref, name):
    return INST[ref].pin(name)[1]


# --- P1: маленькая плата питания, вверху по центру
P1_X, P1_Y = OX + 5400, 1200
place("P1", "p1", P1_X, P1_Y, "P1 питание 3V3/GND (25×8 мм)", label_at=(P1_X - 300, 420))

# --- TCA9548A повёрнут: каналы 2–5 сверху (к пальцам), питание, I²C и каналы 0–1 снизу
place("A2", "tca", OX + 6000, 4000, "A2 TCA9548A (0x70)", rot=-90, label_at=(OX + 7100, 4560))

# --- 4 пальца сверху: порядок слева направо совпадает с порядком каналов на TCA (5, 4, 3, 2)
TOP = [("U6", 5, "U6 ch5 мизинец"), ("U5", 4, "U5 ch4 безымянный"),
       ("U4", 3, "U4 ch3 средний"), ("U3", 2, "U3 ch2 указательный")]
_, bvx, bvy = PARTS["bno"].pins["VCC"]
for i, (ref, ch, cap) in enumerate(TOP):
    v = OX + 6200 + 1600 * (i - 1.5)
    place(ref, "bno", v - bvx, 3000 - bvy, cap)

# --- большой палец и ладонь — под TCA, повёрнуты пинами вверх
place("U2", "bno", OX + 7700, 5480, "U2 ch1 большой", rot=180, label_at=(OX + 7700, 6370))
place("U1", "bno", OX + 6500, 6830, "U1 ch0 ладонь (на тыле кисти)", rot=180, label_at=(OX + 6500, 7740))

# --- ESP32-C3 под TCA слева, USB-C вниз
place("A1", "esp", OX + 5000, 5500, "A1 ESP32-C3 SuperMini", rot=180, label_at=(OX + 5000, 6520))

# --- браслет питания (слева снизу): АКБ → TP4056 → SW1 → MT3608 → D1 → ESP 5V
BX = OX - 3801
place("A3", "mt3608", OX + 2800, 7000, "A3 MT3608 (5,0–5,1 В)", rot=180, label_at=(OX + 2800, 7730))
d1 = place("D1", "diode", 0, 0, "D1", rot=180)
d1.props = {"part number": "1N5819"}
vx, vy = P("A3", "VOUT+")
ax, ay = P("D1", "A")
d1.x, d1.y = (vx + 150) - ax, vy - ay
d1.label_at = (d1.bbox()[0], d1.bbox()[3] + 60)
place("SW1", "switch", OX + 2199, 6969.6, "SW1", label_at=(OX + 2199, 6780))
tp = place("A4", "tp4056", OX + 1249.4, 6400, "A4 Type-C", rot=90)
tp.props = {"part number": "TP4056"}
tp.label_at = (tp.bbox()[0], 7520)
place("GB1", "lipo", OX - 2151, 4700, "GB1 Li-Pol 3,7 В 1300 мА·ч", rot=90)

# ============================================================================ провода

COLORS = {"3v3": "#cc1414", "gnd": "#404040", "sda": "#418dd9", "scl": "#ffe24d", "5v": "#ff7033",
          "bat": "#ab58a2"}
WIRES: list[dict] = []


def wire(color, a, b, via=()):
    """a, b: (обозначение, пин). via: точки изгиба (мил)."""
    ia, pa = INST[a[0]].pin(a[1])
    ib, pb = INST[b[0]].pin(b[1])
    WIRES.append({"color": COLORS[color], "pts": [pa, *via, pb], "a": (a[0], ia), "b": (b[0], ib)})


# --- данные пальцев: SDA (ATX) и SCL (LRX) прямо на пины канала TCA, веером сверху
for i, (ref, ch, cap) in enumerate(TOP):
    moving_right = P("A2", f"SD{ch}")[0] > P(ref, "ATX")[0]
    outer = i in (0, 3)
    base = 4150 if outer else 3750
    for j, (sp, tp_) in enumerate((("ATX", f"SD{ch}"), ("LRX", f"SC{ch}"))):
        sx, _ = P(ref, sp)
        tx, _ = P("A2", tp_)
        lvl = base - (j if moving_right else 1 - j) * 100
        wire("sda" if sp == "ATX" else "scl", (ref, sp), ("A2", tp_), [(sx, lvl), (tx, lvl)])

# --- данные большого пальца и ладони: снизу вверх на пины каналов 1 и 0
for ref, ch, lv in (("U2", 1, 5200), ("U1", 0, 5300)):
    for j, (sp, tp_) in enumerate((("ATX", f"SD{ch}"), ("LRX", f"SC{ch}"))):
        sx, _ = P(ref, sp)
        tx, _ = P("A2", tp_)
        lvl = lv + j * 50
        wire("sda" if sp == "ATX" else "scl", (ref, sp), ("A2", tp_), [(sx, lvl), (tx, lvl)])

# --- питание датчиков, TCA и ESP: всё на P1. Верхний ряд P1 — 3V3, нижний — GND.
# Порядок штырей подобран так, чтобы провода к P1 не перекрещивались.
V_PINS = ["U5", "A2", "A1", "U6", "U1", "U2", "U3", "U4"]   # 3V3.1 … 3V3.8 слева направо
G_PINS = ["U6", "A1", "A2", "U5", "U4", "U3", "U2", "U1"]   # GND.1 … GND.8
V_LVL = {"U6": 700, "A1": 775, "A2": 850, "U5": 925, "U1": 700, "U2": 775, "U3": 850, "U4": 925}
G_LVL = {"U6": 1750, "A1": 1825, "A2": 1900, "U5": 1975, "U1": 1750, "U2": 1825, "U3": 1900, "U4": 1975}


def to_p1(color, ref, pin, row, path):
    """Провод от пина к своему штырю P1: path — точки до подъёма, затем уровень и вход в штырь."""
    pins = V_PINS if row == "3V3" else G_PINS
    lvl = (V_LVL if row == "3V3" else G_LVL)[ref]
    p1pin = f"{row}.{pins.index(ref) + 1}"
    px, _ = P("P1", p1pin)
    lane_x = path[-1][0]
    wire(color, (ref, pin), ("P1", p1pin), [*path, (lane_x, lvl), (px, lvl)])


# пальцы сверху: вниз от пинов, влево в промежуток между датчиками, вверх к P1
for ref, ch, cap in TOP:
    vx_, vy_ = P(ref, "VCC")
    gx_, gy_ = P(ref, "GND")
    to_p1("3v3", ref, "VCC", "3V3", [(vx_, vy_ + 100), (vx_ - 250, vy_ + 100)])
    to_p1("gnd", ref, "GND", "GND", [(gx_, gy_ + 150), (vx_ - 350, gy_ + 150)])
# TCA: VIN/GND с нижнего ряда — вниз, влево за край TCA, вверх
for pin, row, color, depth, lane in (("VIN", "3V3", "3v3", 100, OX + 4950), ("GND", "GND", "gnd", 150, OX + 4875)):
    x, y = P("A2", pin)
    to_p1(color, "A2", pin, row, [(x, y + depth), (lane, y + depth)])
# ESP: 3.3 и G — влево, вверх
for pin, row, color, lane in (("3.3", "3V3", "3v3", OX + 4800), ("G", "GND", "gnd", OX + 4725)):
    x, y = P("A1", pin)
    to_p1(color, "A1", pin, row, [(lane, y)])
# большой палец и ладонь: вверх над датчиком, вправо к правому краю, вверх
for ref, (gl, vl), (glane, vlane) in (("U2", (5420, 5450), (OX + 9700, OX + 9775)),
                                      ("U1", (6650, 6700), (OX + 9850, OX + 9925))):
    gx_, gy_ = P(ref, "GND")
    vx_, vy_ = P(ref, "VCC")
    to_p1("gnd", ref, "GND", "GND", [(gx_, gl), (glane, gl)])
    to_p1("3v3", ref, "VCC", "3V3", [(vx_, vl), (vlane, vl)])

# --- I²C хоста: GPIO5 = SDA, GPIO4 = SCL
x4, y4 = P("A1", "GPIO4")
tx, ty = P("A2", "SCL")
esp_top = INST["A1"].bbox()[1]
wire("scl", ("A1", "GPIO4"), ("A2", "SCL"), [(x4 - 100, y4), (x4 - 100, esp_top - 120), (tx, esp_top - 120)])
x5, y5 = P("A1", "GPIO5")
tx, ty = P("A2", "SDA")
wire("sda", ("A1", "GPIO5"), ("A2", "SDA"), [(tx, y5)])

# --- браслет питания → ESP: 5V через диод, GND напрямую
ox, oy = P("A4", "OUT-")
vx, vy = P("A3", "VIN-")
wire("gnd", ("A4", "OUT-"), ("A3", "VIN-"), [(ox - 150, oy), (ox - 150, 6500), (OX + 2700, 6500), (OX + 2700, vy)])
ox, oy = P("A4", "OUT+")
cx, cy = P("SW1", "COM")
wire("bat", ("A4", "OUT+"), ("SW1", "COM"), [(ox - 250, oy), (ox - 250, 7450), (cx, 7450)])
lx, ly = P("SW1", "L2")
vx, vy = P("A3", "VIN+")
wire("bat", ("SW1", "L2"), ("A3", "VIN+"), [(lx, vy)])
bx, by = P("A4", "B-")
gx, gy = P("GB1", "-")
wire("gnd", ("A4", "B-"), ("GB1", "-"), [(gx + 150, by), (gx + 150, gy)])
bx, by = P("A4", "B+")
gx, gy = P("GB1", "+")
wire("bat", ("A4", "B+"), ("GB1", "+"), [(gx + 80, by), (gx + 80, gy)])
wire("5v", ("A3", "VOUT+"), ("D1", "A"))
kx, ky = P("D1", "K")
ex, ey = P("A1", "5V")
wire("5v", ("D1", "K"), ("A1", "5V"), [(OX + 4700, ky), (OX + 4700, ey)])
gx, gy = P("A3", "VOUT-")
ex, ey = P("A1", "G")
wire("gnd", ("A3", "VOUT-"), ("A1", "G"), [(OX + 4550, gy), (OX + 4550, ey)])


# ============================================================================ запись .fz

NOTES = [
    (0, 200, 3800, 2300,
     "<b>AirGlove — схема соединений (макет)</b><br>Модули как в реальности: ESP32-C3 SuperMini, TCA9548A, "
     "6× GY-BNO055 (фиолетовый CJMCU-055), TP4056 Type-C с защитой, MT3608, Li-Pol 1300 мА·ч.<br>"
     "Подключение: SDA и SCL каждого датчика идут прямо на его канал TCA9548A (SDx/SCx). VCC и GND всех датчиков, TCA9548A и ESP32-C3 собраны на маленькой плате P1 (25×8 мм): верхний ряд штырей — 3V3, нижний — GND. P1 питается от 3.3 и G ESP32-C3. Браслет питания подключён к 5V и G ESP32-C3.<br>"
     "Цвета проводов: красный 3V3, чёрный GND, синий SDA, жёлтый SCL, оранжевый 5V, фиолетовый АКБ.<br>"
     "Каналы TCA9548A по ТЗ (НФТ-2): 0 ладонь, 1 большой, 2 указательный, 3 средний, 4 безымянный, 5 мизинец. "
     "I²C хоста: SDA = GPIO5, SCL = GPIO4."),
    (0, 2700, 3800, 1800,
     "<b>Важно</b><br>1. Когда USB-C ESP подключён к ноутбуку, SW1 выключен.<br>"
     "2. MT3608 выставить на 5,0–5,1 В до подключения к P1/ESP.<br>"
     "3. GND системы = OUT− TP4056. B− — только к аккумулятору.<br>"
     "4. TCA9548A: A0–A2 и RST не подключены → адрес 0x70.<br>"
     "5. GY-BNO055: ATX = SDA, LRX = SCL, перемычки S0/S1 на GND (режим I²C), адрес 0x28 или 0x29. "
     "Все 6 датчиков на разных каналах TCA, поэтому одинаковые адреса не мешают.<br>"
     "6. На P1 все штыри верхнего ряда одинаковые (3V3), нижнего — тоже (GND): провод можно надеть на любой."),
]

WIRE_VIEWS = [("breadboardView", "breadboardWire", "breadboard", "22.2222"),
              ("schematicView", "schematicTrace", "schematic", "9.7222"),
              ("pcbView", "copper1trace", "copper1", "24")]


def note_html(body):
    paras = "".join(f'<p style=" margin-top:0px; margin-bottom:4px;">{line_}</p>' for line_ in body.split("<br>"))
    return h('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">'
             '<html><head><meta name="qrichtext" content="1" /></head>'
             f'<body style=" font-family:\'Droid Sans\'; font-size:9pt;">{paras}</body></html>')


def part_connectors(inst: Inst, part_layer: str, wire_layer: str, with_legs: bool, with_direct: bool = True) -> str:
    out = []
    names = {i: n for n, (i, _, _) in inst.part.pins.items()}
    keys = set(inst.conns) | (set(inst.direct) if with_direct else set())
    for ci in sorted(keys):
        cs = "".join(f'<connect connectorId="{end}" modelIndex="{seg}" layer="{wire_layer}"/>'
                     for seg, end in inst.conns.get(ci, []))
        if with_direct:  # модуль вставлен в гнездо P1 — соединение без провода
            cs += "".join(f'<connect connectorId="connector{oci}" modelIndex="{INST[oref].index}" layer="{part_layer}"/>'
                          for oref, oci in inst.direct.get(ci, []))
        leg = inst.part.legs.get(names[ci]) if with_legs else None
        if leg:
            x0, y0, dx, dy = leg
            geo = (f'<geometry x="{x0}" y="{y0}"/><leg><point x="0" y="0"/><bezier/>'
                   f'<point x="{dx}" y="{dy}"/><bezier/></leg>')
        else:
            geo = '<geometry x="0" y="0"/>'
        out.append(f'<connector connectorId="connector{ci}" layer="{part_layer}">{geo}<connects>{cs}</connects></connector>')
    return "".join(out)


def build_fz() -> str:
    mi = 5000
    for inst in INST.values():
        inst.index = mi
        mi += 1
    for w in WIRES:
        w["segs"] = list(range(mi, mi + len(w["pts"]) - 1))
        mi += len(w["segs"])
    for w in WIRES:
        INST[w["a"][0]].conns.setdefault(w["a"][1], []).append((w["segs"][0], "connector0"))
        INST[w["b"][0]].conns.setdefault(w["b"][1], []).append((w["segs"][-1], "connector1"))
    for ra, pa, rb, pb in DIRECT:
        ia, ib = INST[ra].part.pins[pa][0], INST[rb].part.pins[pb][0]
        INST[ra].direct.setdefault(ia, []).append((rb, ib))
        INST[rb].direct.setdefault(ib, []).append((ra, ia))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<module fritzingVersion="0.9.4" icon=".png">',
           ' <views>',
           '  <view name="breadboardView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="0" alignToGrid="1" viewFromBelow="0"/>',
           '  <view name="schematicView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>',
           '  <view name="pcbView" backgroundColor="#333333" gridSize="0.05in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>',
           ' </views>',
           ' <instances>']
    z = 2.5
    pcb_x = 0.0
    # расстановка символов в схеме (px): P1 слева, модули и датчики справа, питание снизу
    sch_pos = {"P1": (0, 0), "A2": (200, 0), "A1": (380, 0), "A3": (200, 330), "D1": (400, 330),
               "SW1": (520, 330), "A4": (640, 330), "GB1": (820, 330)}
    for i, ref in enumerate(("U1", "U2", "U3", "U4", "U5", "U6")):
        sch_pos[ref] = (560 + 175 * (i % 3), 0 + 110 * (i // 3))
    for ref, inst in INST.items():
        p = inst.part
        sch_x, sch_y = sch_pos.get(ref, (0, 600))
        z += 0.0001
        lx, ly = inst.label_at or (inst.bbox()[0], inst.bbox()[1] - 180)
        visible = "true"
        props = "".join(f'<property name="{h(k)}" value="{h(v)}"/>' for k, v in inst.props.items())
        xml.append(f'''  <instance moduleIdRef="{p.mid}" modelIndex="{inst.index}" path="{h(p.path)}">
   {props}
   <title>{h(inst.caption or ref)}</title>
   <views>
    <breadboardView layer="breadboard">
     <geometry z="{z:.5f}" x="{inst.x * PX:.4f}" y="{inst.y * PX:.4f}">{transform_xml(p, inst.rot)}</geometry>
     <titleGeometry visible="{visible}" x="{lx * PX:.4f}" y="{ly * PX:.4f}" z="{z + 10:.5f}" xOffset="0" yOffset="0" textColor="#000000" fontSize="9"/>
     <connectors>{part_connectors(inst, "breadboard", "breadboardWire", True)}</connectors>
    </breadboardView>
    <schematicView layer="schematic">
     <geometry z="{z:.5f}" x="{sch_x:.4f}" y="{sch_y:.4f}"/>
     <connectors>{part_connectors(inst, "schematic", "schematicTrace", False)}</connectors>
    </schematicView>
    <pcbView layer="copper0">
     <geometry z="{z:.5f}" x="{pcb_x:.4f}" y="0"/>
     <connectors>{part_connectors(inst, "copper1", "copper1trace", False)}</connectors>
    </pcbView>
   </views>
  </instance>''')
        pcb_x += p.w * PX + 30

    wz = 3.5
    for w in WIRES:
        pts, segs = w["pts"], w["segs"]
        for si, seg in enumerate(segs):
            (x0, y0), (x1, y1) = pts[si], pts[si + 1]
            wz += 0.0001
            # Провод живёт во всех трёх видах: в breadboard он виден, а в схеме и ПП Fritzing
            # рисует по нему ratsnest (пунктир несведённых связей).
            views = []
            for view, wlayer, player, mils in WIRE_VIEWS:
                if si == 0:
                    c0 = f'<connect connectorId="connector{w["a"][1]}" modelIndex="{INST[w["a"][0]].index}" layer="{player}"/>'
                else:
                    c0 = f'<connect connectorId="connector1" modelIndex="{segs[si - 1]}" layer="{wlayer}"/>'
                if si == len(segs) - 1:
                    c1 = f'<connect connectorId="connector{w["b"][1]}" modelIndex="{INST[w["b"][0]].index}" layer="{player}"/>'
                else:
                    c1 = f'<connect connectorId="connector0" modelIndex="{segs[si + 1]}" layer="{wlayer}"/>'
                views.append(f'''    <{view} layer="{wlayer}">
     <geometry z="{wz:.5f}" x="{x0 * PX:.4f}" y="{y0 * PX:.4f}" x1="0" y1="0" x2="{(x1 - x0) * PX:.4f}" y2="{(y1 - y0) * PX:.4f}" wireFlags="64"/>
     <wireExtras mils="{mils}" color="{w["color"]}" opacity="1" banded="0"/>
     <connectors>
      <connector connectorId="connector0" layer="{wlayer}"><geometry x="0" y="0"/><connects>{c0}</connects></connector>
      <connector connectorId="connector1" layer="{wlayer}"><geometry x="0" y="0"/><connects>{c1}</connects></connector>
     </connectors>
    </{view}>''')
            body = "\n".join(views)
            xml.append(f'''  <instance moduleIdRef="WireModuleID" modelIndex="{seg}" path=":/resources/parts/core/wire.fzp">
   <title>Wire{seg}</title>
   <views>
{body}
   </views>
  </instance>''')

    for ni, (x, y, ww, hh, body) in enumerate(NOTES):
        xml.append(f'''  <instance moduleIdRef="NoteModuleID" modelIndex="{mi + ni}" path=":/resources/parts/core/note.fzp">
   <title>Note{ni + 1}</title>
   <text>{note_html(body)}</text>
   <views>
    <breadboardView layer="breadboardNote">
     <geometry z="20.{ni}" x="{x * PX:.4f}" y="{y * PX:.4f}" width="{ww * PX:.4f}" height="{hh * PX:.4f}"/>
    </breadboardView>
   </views>
  </instance>''')
    xml += [" </instances>", "</module>"]
    return "\n".join(xml)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fz = build_fz()
    with zipfile.ZipFile(FZZ, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AirGlove.fz", fz)
        for p in CUSTOM.values():
            z.writestr(f"part.{p.mid}.fzp", fzp(p))
            z.writestr(f"svg.breadboard.{p.key}_breadboard.svg", bb_svg(p))
            z.writestr(f"svg.schematic.{p.key}_schematic.svg", sch_svg(p))
            z.writestr(f"svg.pcb.{p.key}_pcb.svg", pcb_svg(p))
        for d in sorted({p.vendored for p in EXT_PARTS.values() if p.vendored}):
            for f in sorted(d.iterdir()):
                if f.name.startswith(("part.", "svg.")):
                    z.write(f, f.name)
    n_seg = sum(len(w["segs"]) for w in WIRES)
    print(f"written {FZZ}  parts={len(INST)} wires={len(WIRES)} segments={n_seg}")


if __name__ == "__main__":
    main()
