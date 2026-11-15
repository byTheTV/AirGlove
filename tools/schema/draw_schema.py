"""Генератор схемы соединений AirGlove (docs/schema.svg).

Схема нарисована по реальным модулям макета, а не по деталям из библиотеки Fritzing.
Запуск:  python tools/schema/draw_schema.py
PNG:     python tools/schema/render_png.py   (рендер через headless Chrome/Edge)

Подписи пинов совпадают с шелкографией модулей. Порядок пинов у ESP32-C3 SuperMini
и у датчиков реальный; у TCA9548A пины сгруппированы логически (на модуле два ряда по 12).
"""
from pathlib import Path

W, H = 2800, 2330
FONT = "Segoe UI, Arial, Helvetica, sans-serif"

C = {
    "3v3": "#e53935",
    "gnd": "#212121",
    "sda": "#1e88e5",
    "scl": "#f4b400",
    "v5": "#fb8c00",
    "vbat": "#8e0000",
    "nc": "#9e9e9e",
}

out: list[str] = []


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=18, anchor="start", color="#212121", weight="normal", style=""):
    lines = s.split("\n")
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{x}" y="{y + i * size * 1.25:.1f}" font-family="{FONT}" font-size="{size}" '
            f'text-anchor="{anchor}" fill="{color}" font-weight="{weight}" {style}>{esc(line)}</text>'
        )


def rect(x, y, w, h, fill, stroke="#000", sw=2, rx=10, extra=""):
    out.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}" {extra}/>'
    )


def wire(points, color, width=5):
    d = " ".join(f"{x},{y}" for x, y in points)
    if color == C["scl"]:  # жёлтый на белом плохо видно: даём тёмную окантовку
        out.append(f'<polyline points="{d}" fill="none" stroke="#7a5a00" stroke-width="{width + 3}" '
                   f'stroke-linejoin="round" stroke-linecap="round"/>')
    out.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')


def dot(x, y, color="#000", r=8):
    out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" stroke="#000" stroke-width="1.5"/>')


def pin(x, y, label, side, used=True, label_color="#fff", size=16):
    fill = "#d4af37" if used else "#cfcfcf"
    out.append(f'<circle cx="{x}" cy="{y}" r="8" fill="{fill}" stroke="#5d4a00" stroke-width="2"/>')
    if side == "left":
        text(x + 16, y + 6, label, size=size, color=label_color if used else "#bdbdbd")
    else:
        text(x - 16, y + 6, label, size=size, anchor="end", color=label_color if used else "#bdbdbd")


def nc_mark(x, y, side):
    dx = -22 if side == "left" else 22
    out.append(f'<line x1="{x}" y1="{y}" x2="{x + dx}" y2="{y}" stroke="{C["nc"]}" stroke-width="2"/>')
    out.append(f'<line x1="{x + dx - 6}" y1="{y - 6}" x2="{x + dx + 6}" y2="{y + 6}" stroke="{C["nc"]}" stroke-width="2"/>')
    out.append(f'<line x1="{x + dx - 6}" y1="{y + 6}" x2="{x + dx + 6}" y2="{y - 6}" stroke="{C["nc"]}" stroke-width="2"/>')


# ---------------------------------------------------------------- рамка и заголовок
out.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
text(60, 70, "AirGlove — схема электрическая соединений (макет)", size=40, weight="bold")
text(60, 112, "Нарисована по реальным модулям: ESP32-C3 SuperMini, TCA9548A, 6× GY-BNO055 (CJMCU-055), "
     "TP4056 Type-C с защитой, MT3608", size=21, color="#555")

# легенда
lx, ly = 2060, 40
rect(lx, ly, 690, 150, "#fafafa", stroke="#bbb", sw=1.5, rx=8)
legend = [("3V3", C["3v3"]), ("GND", C["gnd"]), ("SDA", C["sda"]), ("SCL", C["scl"]),
          ("5V (MT3608 → ESP)", C["v5"]), ("АКБ / после TP4056", C["vbat"])]
for i, (name, col) in enumerate(legend):
    cx = lx + 25 + (i % 2) * 340
    cy = ly + 35 + (i // 2) * 42
    wire([(cx, cy), (cx + 60, cy)], col, 7)
    text(cx + 75, cy + 7, name, size=19)

# ---------------------------------------------------------------- ESP32-C3 SuperMini
EX, EY, EW, EH = 300, 330, 240, 430
rect(EX, EY, EW, EH, "#1b1b1b", rx=14)
rect(EX + 80, EY - 22, 80, 46, "#b0b0b0", stroke="#555", sw=2, rx=8)  # USB-C
text(EX + 120, EY - 34, "USB-C: прошивка и отладка", size=17, anchor="middle", color="#333")
text(EX + EW / 2, EY + 95, "ESP32-C3", size=24, anchor="middle", color="#fff", weight="bold")
text(EX + EW / 2, EY + 122, "SuperMini", size=20, anchor="middle", color="#ddd")
rect(EX + 70, EY + EH - 50, 100, 30, "#3a3a3a", stroke="#777", sw=1.5, rx=4)
text(EX + EW / 2, EY + EH - 29, "антенна", size=15, anchor="middle", color="#ccc")
text(EX + EW / 2, EY + EH + 32, "A1 — ESP32-C3 SuperMini", size=19, anchor="middle", weight="bold")

ESP_L = ["5V", "G", "3.3", "4", "3", "2", "1", "0"]
ESP_R = ["5", "6", "7", "8", "9", "10", "20", "21"]
esp_pin = {}
for i, name in enumerate(ESP_L):
    y = EY + 80 + i * 40
    esp_pin["L" + name] = (EX, y)
    pin(EX, y, name, "left", used=name in ("5V", "G", "3.3", "4"))
for i, name in enumerate(ESP_R):
    y = EY + 80 + i * 40
    esp_pin["R" + name] = (EX + EW, y)
    pin(EX + EW, y, name, "right", used=name == "5")

# ---------------------------------------------------------------- TCA9548A
TX, TY, TW, TH = 900, 330, 260, 750
rect(TX, TY, TW, TH, "#1f4fa0", rx=12)
text(TX + TW / 2, TY + 45, "TCA9548A", size=24, anchor="middle", color="#fff", weight="bold")
text(TX + TW / 2, TY + 70, "I²C-мультиплексор", size=16, anchor="middle", color="#dfe8ff")
text(TX + TW / 2, TY + TH + 32, "A2 — TCA9548A, адрес 0x70", size=19, anchor="middle", weight="bold")
TCA_L = ["VIN", "GND", "SDA", "SCL", "RST", "A0", "A1", "A2"]
tca = {}
for i, name in enumerate(TCA_L):
    y = TY + 110 + i * 40
    tca[name] = (TX, y)
    pin(TX, y, name, "left", used=i < 4)
    if i >= 4:
        nc_mark(TX, y, "left")
for ch in range(8):
    for j, kind in enumerate(("SD", "SC")):
        y = TY + 110 + ch * 80 + j * 40
        tca[f"{kind}{ch}"] = (TX + TW, y)
        pin(TX + TW, y, f"{kind}{ch}", "right", used=ch < 6)
        if ch >= 6:
            nc_mark(TX + TW, y, "right")
text(TX + 30, TY + 110 + 6 * 80 + 46, "каналы 6–7:\nрезерв", size=16, color="#b9c8ee")

# ---------------------------------------------------------------- датчики
SX, SW_, SH = 2250, 400, 225
SENSORS = [  # все 6 датчиков — фиолетовые GY-BNO055 (CJMCU-055)
    (0, "ладонь (тыл кисти)", "GY-BNO055"),
    (1, "большой палец", "GY-BNO055"),
    (2, "указательный (курсор)", "GY-BNO055"),
    (3, "средний", "GY-BNO055"),
    (4, "безымянный", "GY-BNO055"),
    (5, "мизинец", "GY-BNO055"),
]
BNO_PINS = ["VCC", "GND", "ATX = SDA", "LRX = SCL", "I2C", "INT", "RES", "BOOT"]


def sensor_top(k):
    return 300 + k * 250


sensor_pin = {}
for k, finger, kind in SENSORS:
    y0 = sensor_top(k)
    rect(SX, y0, SW_, SH, "#5e2b97", rx=12)
    for i, name in enumerate(BNO_PINS):
        y = y0 + 25 + i * 20
        used = i < 4
        sensor_pin[(k, name.split(" ")[0])] = (SX, y)
        pin(SX, y, name, "left", used=used, size=14)
    tx = SX + 170
    text(tx, y0 + 34, f"ch{k}", size=26, color="#fff", weight="bold")
    text(tx, y0 + 62, finger, size=17, color="#fff")
    text(tx, y0 + 90, kind, size=19, color="#fff", weight="bold")
    note = "адрес 0x28 / 0x29\nS0, S1 → GND (I²C)\nI2C, INT, RES, BOOT — NC"
    text(tx, y0 + 120, note, size=14, color="#e8e8ff")
    text(SX + SW_ + 14, y0 + 30, f"U{k + 1}", size=18, weight="bold")

# ---------------------------------------------------------------- P1: плата распределения
PX, PY, PW, PH = 1560, 215, 230, 1660
RAIL3, RAILG = 1640, 1690
JX = PX + PW
rect(PX, PY, PW, PH, "#e8f1e4", stroke="#5b8c4a", sw=3, rx=10,
     extra='stroke-dasharray="12 6"')
text(PX + PW / 2, PY - 52, "P1 — плата распределения", size=20, anchor="middle", weight="bold")
text(PX + PW / 2, PY - 28, "(макетка / пластина на кисти)", size=16, anchor="middle", color="#555")
wire([(RAIL3, 270), (RAIL3, 1820)], C["3v3"], 9)
wire([(RAILG, 240), (RAILG, 1860)], C["gnd"], 9)
text(RAIL3 - 8, 1500, "шина 3V3", size=16, color=C["3v3"], weight="bold",
     style=f'transform="rotate(-90 {RAIL3 - 8} 1500)"')
text(RAILG + 26, 1500, "шина GND", size=16, color=C["gnd"], weight="bold",
     style=f'transform="rotate(-90 {RAILG + 26} 1500)"')

# ---------------------------------------------------------------- сигнальные линии TCA → J → датчик
for k, finger, kind in SENSORS:
    y0 = sensor_top(k)
    jy = [y0 + 25 + i * 20 for i in range(4)]  # J: 3V3, GND, SDA, SCL
    base = 1500 - k * 44
    sd_x, sc_x = base, base - 20
    sdy, scy = tca[f"SD{k}"][1], tca[f"SC{k}"][1]
    wire([(TX + TW, sdy), (sd_x, sdy), (sd_x, jy[2]), (JX, jy[2])], C["sda"], 4)
    wire([(TX + TW, scy), (sc_x, scy), (sc_x, jy[3]), (JX, jy[3])], C["scl"], 4)
    # питание от шин P1
    wire([(RAIL3, jy[0]), (JX, jy[0])], C["3v3"], 4)
    dot(RAIL3, jy[0], C["3v3"], 7)
    wire([(RAILG, jy[1]), (JX, jy[1])], C["gnd"], 4)
    dot(RAILG, jy[1], C["gnd"], 7)
    # разъём Jk на краю P1
    rect(JX - 6, jy[0] - 14, 30, 88, "#333", stroke="#000", sw=1.5, rx=3)
    for i in range(4):
        out.append(f'<circle cx="{JX + 9}" cy="{jy[i]}" r="5" fill="#d4af37"/>')
    text(JX + 34, jy[0] - 18, f"J{k}", size=16, weight="bold")
    # кабель к датчику
    s = {n: sensor_pin[(k, n)] for n in ("VCC", "GND", "ATX", "LRX")}
    wire([(JX + 24, jy[0]), s["VCC"]], C["3v3"], 4)
    wire([(JX + 24, jy[1]), s["GND"]], C["gnd"], 4)
    wire([(JX + 24, jy[2]), s["ATX"]], C["sda"], 4)
    wire([(JX + 24, jy[3]), s["LRX"]], C["scl"], 4)
    text(2020, jy[3] + 40, "кабель 4 пр., 15–20 см", size=13, anchor="middle", color="#666")

# ---------------------------------------------------------------- ESP ↔ TCA (I²C хоста)
wire([esp_pin["R5"], (760, esp_pin["R5"][1]), (760, tca["SDA"][1]), tca["SDA"]], C["sda"], 5)
g4 = esp_pin["L4"]
wire([g4, (270, g4[1]), (270, 840), (800, 840), (800, tca["SCL"][1]), tca["SCL"]], C["scl"], 5)
text(620, 470, "GPIO5 = SDA", size=16, color=C["sda"], weight="bold")
text(560, 868, "GPIO4 = SCL", size=16, color="#7a5a00", weight="bold")

# питание TCA от шин P1
wire([tca["VIN"], (860, tca["VIN"][1]), (860, 270), (RAIL3, 270)], C["3v3"], 5)
dot(RAIL3, 270, C["3v3"], 7)
wire([tca["GND"], (840, tca["GND"][1]), (840, 240), (RAILG, 240)], C["gnd"], 5)
dot(RAILG, 240, C["gnd"], 7)

# питание P1 от ESP: 3.3 → шина 3V3, G → шина GND
p33 = esp_pin["L3.3"]
wire([p33, (240, p33[1]), (240, 1820), (RAIL3, 1820)], C["3v3"], 6)
dot(RAIL3, 1820, C["3v3"], 7)
pg = esp_pin["LG"]
wire([pg, (210, pg[1]), (210, 1860), (RAILG, 1860)], C["gnd"], 6)
dot(RAILG, 1860, C["gnd"], 7)
text(250, 1808, "3V3 со стабилизатора ESP (датчики + TCA < 100 мА)", size=16, color=C["3v3"])
text(250, 1890, "общий GND", size=16, color="#000")

# ---------------------------------------------------------------- питание: АКБ → TP4056 → SW1 → MT3608 → D1 → 5V
PYV = 2010  # верхняя линия цепи питания
PYL = 2080  # нижняя линия

# MT3608
MX, MW = 1000, 330
rect(MX, PYV - 40, MW, 150, "#1565c0", rx=10)
text(MX + MW / 2, PYV + 25, "MT3608", size=22, anchor="middle", color="#fff", weight="bold")
text(MX + MW / 2, PYV + 50, "повышающий DC-DC", size=15, anchor="middle", color="#e3f2fd")
text(MX + MW / 2, PYV + 72, "выставить 5,0–5,1 В!", size=15, anchor="middle", color="#ffeb3b", weight="bold")
text(MX + MW / 2, PYV + 140, "A3 — MT3608", size=18, anchor="middle", weight="bold")
mt = {"VOUT-": (MX, PYV), "VOUT+": (MX, PYL), "VIN+": (MX + MW, PYV), "VIN-": (MX + MW, PYL)}
pin(MX, PYV, "VOUT−", "left", size=14)
pin(MX, PYL, "VOUT+", "left", size=14)
pin(MX + MW, PYV, "VIN+", "right", size=14)
pin(MX + MW, PYL, "VIN−", "right", size=14)

# TP4056
TPX, TPW = 1560, 340
rect(TPX, PYV - 40, TPW, 150, "#0d47a1", rx=10)
text(TPX + TPW / 2, PYV + 25, "TP4056 Type-C", size=22, anchor="middle", color="#fff", weight="bold")
text(TPX + TPW / 2, PYV + 50, "с защитой DW01 + 8205A", size=15, anchor="middle", color="#e3f2fd")
rect(TPX + TPW / 2 - 40, PYV + 92, 80, 34, "#b0b0b0", stroke="#555", sw=2, rx=8)
text(TPX + TPW / 2, PYV + 150, "USB-C: только зарядка", size=16, anchor="middle", color="#333")
text(TPX + TPW / 2, PYV + 175, "A4 — TP4056", size=18, anchor="middle", weight="bold")
tp = {"OUT+": (TPX, PYV), "OUT-": (TPX, PYL), "B+": (TPX + TPW, PYV), "B-": (TPX + TPW, PYL)}
pin(TPX, PYV, "OUT+", "left", size=14)
pin(TPX, PYL, "OUT−", "left", size=14)
pin(TPX + TPW, PYV, "B+", "right", size=14)
pin(TPX + TPW, PYL, "B−", "right", size=14)

# АКБ
BX = 2060
rect(BX, PYV - 50, 420, 170, "#d9d9d9", stroke="#777", sw=2, rx=10)
rect(BX + 340, PYV - 50, 80, 170, "#f2c94c", stroke="#777", sw=2, rx=10)
text(BX + 170, PYV + 30, "Li-Pol 3,7 В", size=24, anchor="middle", weight="bold", color="#444")
text(BX + 170, PYV + 60, "1000–1300 мА·ч, с защитой", size=16, anchor="middle", color="#555")
text(BX + 210, PYV + 155, "GB1 — аккумулятор", size=18, anchor="middle", weight="bold")
wire([tp["B+"], (BX, PYV)], C["vbat"], 6)
wire([tp["B-"], (BX, PYL)], C["gnd"], 6)
text(BX + 10, PYV - 8, "+", size=22, weight="bold")
text(BX + 10, PYL + 28, "−", size=22, weight="bold")

# SW1 на линии OUT+ → VIN+
s1, s2 = 1410, 1490
wire([tp["OUT+"], (s2, PYV)], C["vbat"], 6)
wire([(s1, PYV), mt["VIN+"]], C["vbat"], 6)
out.append(f'<circle cx="{s1}" cy="{PYV}" r="7" fill="#fff" stroke="#000" stroke-width="3"/>')
out.append(f'<circle cx="{s2}" cy="{PYV}" r="7" fill="#fff" stroke="#000" stroke-width="3"/>')
out.append(f'<line x1="{s1 + 6}" y1="{PYV - 4}" x2="{s2 - 4}" y2="{PYV - 34}" stroke="#000" stroke-width="4"/>')
text((s1 + s2) / 2, PYV - 48, "SW1 тумблер", size=16, anchor="middle", weight="bold")
wire([tp["OUT-"], mt["VIN-"]], C["gnd"], 6)
text(1445, PYL + 30, "OUT− = GND системы (не B−!)", size=14, anchor="middle", color="#000")

# VOUT− → общий GND
wire([mt["VOUT-"], (960, PYV), (960, 1860)], C["gnd"], 6)
dot(960, 1860, C["gnd"], 8)

# VOUT+ → D1 → 5V ESP
DX = 700
wire([mt["VOUT+"], (DX + 40, PYL)], C["v5"], 6)
wire([(DX - 40, PYL), (150, PYL), (150, esp_pin["L5V"][1]), esp_pin["L5V"]], C["v5"], 6)
out.append(f'<polygon points="{DX + 30},{PYL - 22} {DX + 30},{PYL + 22} {DX - 12},{PYL}" fill="#333"/>')
out.append(f'<line x1="{DX - 14}" y1="{PYL - 24}" x2="{DX - 14}" y2="{PYL + 24}" stroke="#333" stroke-width="6"/>')
out.append(f'<line x1="{DX - 40}" y1="{PYL}" x2="{DX + 40}" y2="{PYL}" stroke="#333" stroke-width="3"/>')
text(DX, PYL - 36, "D1 1N5819 (Шоттки)", size=16, anchor="middle", weight="bold")
text(DX, PYL + 50, "анод → MT3608, катод → 5V ESP", size=14, anchor="middle", color="#555")
text(170, 700, "5V", size=18, color=C["v5"], weight="bold")

# ---------------------------------------------------------------- примечания
NX, NY = 60, 2185
notes = [
    "1. Когда USB-C ESP подключён к ноутбуку, SW1 выключен: D1 защищает MT3608, но не порт ноутбука.",
    "2. MT3608 настроить на 5,0–5,1 В до подключения к ESP. Нагрузку брать только с OUT± TP4056, B− — только к АКБ.",
    "3. TCA9548A: A0–A2 и RST не подключены (подтяжки на модуле), адрес 0x70. Каналы по ТЗ (НФТ-2): 0 ладонь, 1–5 пальцы.",
    "4. Пины TCA9548A сгруппированы условно (на модуле два ряда по 12), подписи как на плате. NC — не подключать.",
]
for i, n in enumerate(notes):
    text(NX, NY + i * 30, n, size=18, color="#333")
text(W - 60, H - 20, "AirGlove · P3319 · схема v2 по реальным модулям · tools/schema/draw_schema.py",
     size=15, anchor="end", color="#888")

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
       + "\n".join(out) + "\n</svg>\n")
dst = Path(__file__).resolve().parents[2] / "docs" / "schema.svg"
dst.write_text(svg, encoding="utf-8")
print(f"written {dst}")
