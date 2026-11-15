"""Экспорт картинок из docs/fritzing/AirGlove.fzz самим Fritzing.

Fritzing в пакетном режиме (`Fritzing.exe -svg <папка>`) сохраняет breadboard/schematic/pcb в SVG,
а breadboard ещё и рендерится в PNG через headless Chrome/Edge.

Запуск:  python tools/fritzing/export_images.py "C:/путь/к/Fritzing.exe"
         (или задать переменную окружения FRITZING_EXE)
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FZZ = ROOT / "docs" / "fritzing" / "AirGlove.fzz"
OUT = ROOT / "docs" / "fritzing"
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "google-chrome", "chromium"]


def browser() -> str:
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    raise SystemExit("Нужен Chrome или Edge для рендера PNG")


def svg_to_png(svg: Path, png: Path, width_px: int = 3200) -> None:
    text = svg.read_text(encoding="utf-8")
    m = re.search(r"width='([\d.]+)in' height='([\d.]+)in'", text)
    w_in, h_in = float(m.group(1)), float(m.group(2))
    height_px = int(width_px * h_in / w_in)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy(svg, tmp / svg.name)
        page = tmp / "page.html"
        page.write_text(f"<html><body style='margin:0;background:#fff'><img src='{svg.name}' "
                        f"style='width:{width_px}px;height:{height_px}px'></body></html>", encoding="utf-8")
        subprocess.run([browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={tmp / 'profile'}", f"--window-size={width_px},{height_px}",
                        f"--screenshot={png}", page.as_uri()], check=True, timeout=180)


def main() -> None:
    exe = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FRITZING_EXE")
    if not exe:
        raise SystemExit(__doc__)
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(FZZ, Path(tmp) / FZZ.name)
        subprocess.run([exe, "-svg", tmp], cwd=Path(exe).parent, check=True, timeout=300)
        # схема и ПП в проекте не разведены (только ratsnest), поэтому сохраняем только breadboard
        for view in ("breadboard",):
            src = Path(tmp) / f"AirGlove_{view}.svg"
            if src.exists():
                shutil.copy(src, OUT / src.name)
    svg_to_png(OUT / "AirGlove_breadboard.svg", OUT / "AirGlove_breadboard.png")
    print("готово:", ", ".join(p.name for p in sorted(OUT.glob("AirGlove_*"))))


if __name__ == "__main__":
    main()
