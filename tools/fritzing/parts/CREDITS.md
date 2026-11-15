# Детали Fritzing сторонних авторов

Эти детали скачаны и встроены в `docs/fritzing/AirGlove.fzz`. Детали Fritzing обычно
распространяются по CC-BY-SA; авторство сохранено в самих `.fzp`.

Единственное изменение: в `mt3608/svg.breadboard.MT3608_Module_breadboard.svg` содержимое обёрнуто
в `<g id="breadboard">` (в оригинале этот id стоял на корневом `<svg>`, и экспорт Fritzing рисовал
модуль со сдвигом).

| Папка | Деталь | Автор | Источник |
|-------|--------|-------|----------|
| `esp32c3_supermini` | ESP32-C3 SuperMini (THT) | Peter Van Epp (vanepp) | forum.fritzing.org, тема «Need ESP32-C3 super mini board model» |
| `mt3608` | MT3608 Module | Peter Harrison | forum.fritzing.org |
| `tp4056_typec` | TP4056 w/ Protection Type-C | arnab.blue (BlueAG) | github.com/BlueAG/Fritzing-Parts |
| `tca9548a` | Adafruit TCA9548A | ladyada (Adafruit) | github.com/adafruit/Fritzing-Library |
| `lipo_1300mah` | LiPoly Battery (1300mAh) | John De Cristofaro | github.com/adafruit/Fritzing-Library |

Тумблер (`1238DBDC00-toggle-switch`) и диод Шоттки (`145554CBFC44diode`) взяты из стандартной
библиотеки Fritzing и в проект не встраиваются.

Свои детали (генерируются в `build_fzz.py`): GY-BNO055 (фиолетовый CJMCU-055, все 6 датчиков;
готовой детали для этой платы не нашлось — на форуме Fritzing есть только другой клон 12×21 мм
с иной распиновкой) и P1 — наша плата распределения.

Координаты пинов замеряются скриптом `tools/fritzing/measure_pins.py`.
