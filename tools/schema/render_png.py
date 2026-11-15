"""Рендер docs/schema.svg → docs/schema.png через headless Chrome или Edge."""
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SVG = ROOT / "docs" / "schema.svg"
PNG = ROOT / "docs" / "schema.png"
W, H = 2800, 2330
SCALE = 1.25

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "msedge",
]


def find_browser() -> str:
    for c in CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    raise SystemExit("Не найден Chrome/Edge для рендера PNG")


def main() -> None:
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([
            find_browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--user-data-dir={profile}", f"--window-size={W},{H}",
            f"--force-device-scale-factor={SCALE}", f"--screenshot={PNG}", SVG.as_uri(),
        ], check=True, timeout=120)
    print(f"written {PNG}")


if __name__ == "__main__":
    main()
