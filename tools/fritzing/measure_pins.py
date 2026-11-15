"""Замер координат пинов детали Fritzing (центр элемента connectorNpin в breadboard SVG).

Нужен, когда в tools/fritzing/parts добавляется новая деталь: полученные числа переносятся
в таблицу EXT_PARTS в build_fzz.py. Координаты в пикселях сцены Fritzing (90 dpi).

Требует: pip install svgelements==1.9.6
Запуск:  python tools/fritzing/measure_pins.py tools/fritzing/parts/<папка_детали>
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from svgelements import SVG, Group, Shape, Text


def main(folder: Path) -> None:
    fzp = next(folder.glob("part.*.fzp"))
    root = ET.parse(fzp).getroot()
    image = root.find(".//breadboardView/layers").get("image")
    svg_file = folder / ("svg." + image.replace("/", "."))
    svg = SVG.parse(str(svg_file), ppi=90, reify=True)
    centres, texts = {}, []
    for el in svg.elements():
        eid = el.values.get("id") if hasattr(el, "values") else None
        bb = None
        try:
            bb = el.bbox() if isinstance(el, (Shape, Group, Text)) else None
        except Exception:  # у некоторых элементов bbox не считается — пропускаем
            pass
        if not bb:
            continue
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        if isinstance(el, Text) and el.text:
            texts.append((el.text.strip(), cx, cy))
        elif eid:
            centres[eid] = (cx, cy)
    print(f"moduleId={root.get('moduleId')}  size_px=({svg.width:.2f}, {svg.height:.2f})")
    for c in root.iter("connector"):
        p = c.find("./views/breadboardView/p")
        sid = p.get("svgId") if p is not None else None
        pos = centres.get(sid)
        near = ""
        if pos and texts:
            t = min(texts, key=lambda t: (t[1] - pos[0]) ** 2 + (t[2] - pos[1]) ** 2)
            near = f"  ближайшая надпись: {t[0]!r}"
        xy = f"({pos[0]:.2f}, {pos[1]:.2f})" if pos else "нет"
        print(f"{c.get('id'):12} {c.get('name'):10} {xy}{near}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
