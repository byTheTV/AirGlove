# Склеивает docs/model/variants_comparison.png из картинок трёх режимов.
# Запуск из папки tools/model после build_all.sh:  python make_comparison.py
# Нужен Pillow (pip install pillow).
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'model')
MODES = [
    ('dupont_straight', 'A. Dupont прямо (dupont_straight)',
     ['держатель на кончике 27,2 × 26,7 мм, 32,6 / 30,8 мм над пальцем', 'под 47,3 × 54,4 × 31,0 мм', 'браслет 39,6 × 94,2 × 30,6 мм']),
    ('dupont_bent', 'B. Штыри загнуты (dupont_bent)',
     ['держатель на кончике 27,2 × 26,7 мм, 17,7 / 15,9 мм над пальцем', 'под 60,5 × 54,0 × 24,6 мм (2 этажа)', 'браслет 39,6 × 69,8 × 21,4 мм']),
    ('soldered_stubs', 'C. Пайка на пеньки (soldered_stubs)',
     ['держатель на кончике 27,2 × 26,7 мм, 11,6 / 9,8 мм над пальцем', 'под 47,3 × 54,4 × 11,2 мм', 'браслет 39,6 × 55,2 × 19,4 мм']),
]
W, H = 900, 650          # ячейка
TOP = 150                # шапка над колонкой
font_dir = r'C:\Windows\Fonts'
def font(size, bold=False):
    for name in (['arialbd.ttf', 'DejaVuSans-Bold.ttf'] if bold else ['arial.ttf', 'DejaVuSans.ttf']):
        try:
            return ImageFont.truetype(os.path.join(font_dir, name), size)
        except OSError:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
    return ImageFont.load_default()

out = Image.new('RGB', (3*W, TOP + 2*H + 60), (248, 248, 248))
d = ImageDraw.Draw(out)
for i, (m, title, lines) in enumerate(MODES):
    x = i*W
    d.text((x + 30, 18), title, fill=(20, 20, 20), font=font(36, True))
    for k, t in enumerate(lines):
        d.text((x + 30, 66 + k*26), t, fill=(60, 60, 60), font=font(24))
    for r, name in enumerate(['finger_closeup.png', 'assembly_persp.png']):
        im = Image.open(os.path.join(ROOT, m, name)).convert('RGB')
        im.thumbnail((W, H))
        out.paste(im, (x + (W - im.width)//2, TOP + r*H + (H - im.height)//2))
    if i:
        d.line([(x, 10), (x, out.height - 10)], fill=(200, 200, 200), width=3)
d.text((30, out.height - 45), 'Высота держателя — от верха ногтевой фаланги (R 8) до верха крышки, с лентой / с напалком. Корпуса — матовый чёрный PETG.',
       fill=(90, 90, 90), font=font(24))
out.save(os.path.join(ROOT, 'variants_comparison.png'))
print('ok', out.size)
