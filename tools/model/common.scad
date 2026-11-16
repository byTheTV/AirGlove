// =====================================================================
// AirGlove — общие размеры модулей и упрощённые «болванки» плат.
// Подключается в остальные файлы через include <common.scad>.
//
// Все размеры в миллиметрах. Перед печатью ИЗМЕРЬТЕ ШТАНГЕНЦИРКУЛЕМ
// свои платы и поправьте числа ниже: китайские модули одного названия
// отличаются на 0,5–2 мм.
//
// СПОСОБ ПОДКЛЮЧЕНИЯ — один переключатель conn_mode на ВСЕ детали и ВСЕ модули
// с гребёнками (6 × BNO055, ESP32-C3, TCA9548A, P1, TP4056, MT3608):
//   "dupont_straight" — заводская гребёнка, гнёзда Dupont надеты вертикально:
//                       над рядом штырей «столбик» 2,5 + 14 = 16,5 мм + изгиб провода;
//   "dupont_bent"     — штыри загнуты плоскогубцами на 90° у планки (без пайки),
//                       гнёзда лежат плашмя у края платы, провода — к кисти/выходу;
//   "soldered_stubs"  — планка снята, штыри обкусаны до пеньков 1,5 мм,
//                       провода припаяны к пенькам — самые низкие детали.
// Переключается так:  openscad -D 'conn_mode="dupont_bent"' ...
// Ориентация гребёнки (штырями вверх/вниз) задаётся отдельно у ESP, TCA, TP4056, MT3608.
//
// Соглашения для болванок (если не сказано иное):
//   плата лежит в плоскости XY, центр платы в (0,0), низ платы в z = 0.
// =====================================================================

pitch = 2.54;       // шаг штырей

// ---------- Гребёнка штырей 2,54 мм (заводская, как пришла с модулем) ----------
hdr_spacer = 2.5;   // толщина чёрной пластмассовой планки (измерьте: 2,3–2,7)
hdr_pin_up = 6.0;   // длина штыря над планкой (измерьте: 5,8–6,2)
hdr_tail   = 3.0;   // хвост штыря под платой со стороны пайки (измерьте: 2,5–3,0)
hdr_pin_w  = 0.64;  // квадратный штырь 0,64 мм

// ---------- Разъём Dupont «мама» ----------
dup_w      = 2.54;  // сечение корпуса на один контакт (1-pin: 2,54×2,54; 4-pin: 10,16×2,54)
dup_l      = 14.0;  // длина корпуса (измерьте: 13,7–14,5)
dup_bend_r = 5.0;   // радиус изгиба провода на выходе из корпуса
wire_d     = 1.1;   // наружный диаметр провода 28 AWG в силиконе
dup_top    = hdr_spacer + dup_l;            // верх корпуса над платой = 16,5
dup_bend_h = dup_bend_r + wire_d/2;         // запас по высоте на изгиб провода = 5,55

// ---------- Способ подключения (см. шапку файла) ----------
conn_mode = "dupont_straight";   // "dupont_straight" | "dupont_bent" | "soldered_stubs"

// dupont_bent: штырь загибается у верха планки, корпус гнезда лежит плашмя
bent_z    = hdr_spacer + 0.6;   // ось загнутого штыря над платой (3,1)
bent_gap  = 0.8;                // от оси ряда до торца лежачего корпуса (место под изгиб)
bent_lead = 2.0;                // прямой участок провода за корпусом до поворота
// soldered_stubs: планка снята, штыри обкусаны
stub_len  = 1.5;    // пенёк над платой
stub_tail = 1.0;    // хвост с обратной стороны (обкусить до 1 мм)
solder_d  = 1.8;    // капля припоя с проводом

function m_str(m = conn_mode) = m == "dupont_straight";
function m_bent(m = conn_mode) = m == "dupont_bent";
function m_stub(m = conn_mode) = m == "soldered_stubs";
// Высота «разъёма» со стороны штырей, от поверхности платы
function conn_h(m = conn_mode) =
    m_str(m)  ? hdr_spacer + dup_l + dup_bend_h      // 22,05: планка + корпус + изгиб провода
  : m_bent(m) ? bent_z + dup_w/2                     // 4,37: лежачий корпус на загнутом штыре
  :             stub_len + 1.0;                      // 2,5: пенёк + капля припоя + провод
// Хвосты штырей с обратной стороны платы
function tail_h(m = conn_mode) = m_stub(m) ? stub_tail : hdr_tail;
// Насколько разъём (с проводом) уходит в плане от оси ряда в сторону вывода проводов
function conn_run(m = conn_mode) =
    m_str(m)  ? dup_bend_r + wire_d/2                // изгиб провода над корпусом
  : m_bent(m) ? bent_gap + dup_l + bent_lead         // лежачий корпус + выход провода (16,8)
  :             2.5;                                 // припаянный провод уходит плашмя
function mode_name(m = conn_mode) = m_str(m) ? "A: Dupont прямо" : m_bent(m) ? "B: Dupont, штыри загнуты" : "C: пайка на пеньки";

// Цвета проводов датчика: VCC, GND, ATX(SDA), LRX(SCL)
c_wires4 = [[0.85, 0.12, 0.10], [0.10, 0.10, 0.10], [0.15, 0.35, 0.90], [0.95, 0.80, 0.10]];

// ---------- ESP32-C3 SuperMini ----------
esp_l      = 22.5;  // длина платы: от края с USB-C до края с антенной (измерьте)
esp_w      = 18.0;  // ширина платы (измерьте)
esp_pcb    = 1.0;   // толщина платы
esp_row    = 15.24; // расстояние между рядами штырей (измерьте: обычно 15,24)
esp_pins   = 8;     // штырей в ряду
esp_pin_y0 = 0.0;   // сдвиг ряда штырей вдоль платы от центра (+ к антенне)
esp_usb_w  = 9.0;   // ширина корпуса USB-C
esp_usb_h  = 3.3;   // высота корпуса USB-C над платой
esp_usb_l  = 7.4;   // длина корпуса USB-C
esp_usb_out = 1.0;  // насколько USB-C выступает за край платы (измерьте)

// ---------- TCA9548A (плата-мультиплексор) ----------
tca_l     = 31.0;   // длина вдоль рядов контактов (измерьте)
tca_w     = 18.0;   // ширина (измерьте)
tca_pcb   = 1.6;
tca_parts = 1.5;    // высота микросхемы и SMD-деталей
tca_pins  = 12;     // контактов в каждом из двух рядов
tca_row   = 15.24;  // расстояние между рядами (измерьте)
tca_hole_d  = 2.6;  // крепёжные отверстия у коротких краёв
tca_hole_in = 2.5;  // от короткого края до центра отверстия

// ---------- P1: плата питания 3V3/GND (перфоплата 10×3 отверстия) ----------
p1_l       = 25.0;  // длина (измерьте)
p1_w       = 8.0;   // ширина (измерьте)
p1_pcb     = 1.6;
p1_pins    = 8;     // штырей в ряду (ряды: 3V3 и GND, средний ряд пустой)
p1_row     = 2*pitch;   // расстояние между рядами 3V3 и GND = 5,08

// ---------- GY-BNO055 (фиолетовый клон WCMCU-055 / CJMCU-055) ----------
// Плата почти квадратная. Ряд из 8 контактов идёт вдоль края bno_a:
//   VCC, GND, ATX(SDA), LRX(SCL), I2C, INT, RES, BOOT (контакт 1 = VCC у одного конца).
// Подключены только первые 4: на них надет один 4-контактный корпус Dupont.
// Два крепёжных отверстия — в углах ПРОТИВОПОЛОЖНОГО края.
// Ось X на шелкографии — от ряда контактов к отверстиям, ось Y — вдоль ряда.
// Все числа оценены по фото — ИЗМЕРЬТЕ.
bno_a      = 21.0;  // край с рядом контактов (измерьте)
bno_b      = 20.5;  // перпендикулярный край (измерьте)
bno_pcb    = 1.6;   // толщина (измерьте; держатель принимает 1,2–2,0)
bno_npins  = 8;
bno_pin_in = 1.3;   // от края платы до оси ряда контактов (измерьте)
bno_pin1_side = -1; // контакт 1 (VCC) на конце ряда со стороны -X (поменяйте на +1, если наоборот)
bno_hole_d = 2.4;   // диаметр крепёжных отверстий (измерьте)
bno_hole_in = 2.5;  // от обоих краёв до центра отверстия (измерьте)
bno_xtal_d = 2.0;   // кварц 32,768 кГц — цилиндр Ø2×6
bno_xtal_l = 6.0;
bno_xtal_side = 1;  // у какого отверстия кварц (+1 / -1 по X)
bno_xtal_out = 2.0; // насколько кварц может выступать за край платы

function bno_pin_x(i) = bno_pin1_side*(3.5 - i)*pitch;  // контакт i = 0..7
function bno_row_y()  = -bno_b/2 + bno_pin_in;           // ось ряда контактов (край -Y)
function bno_hous_x() = bno_pin1_side*2.0*pitch;          // центр 4-контактного корпуса (контакты 1–4)
function bno_holes()  = [for (s = [-1, 1]) [s*(bno_a/2 - bno_hole_in), bno_b/2 - bno_hole_in]];

// ---------- Питание на браслете ----------
lipo_l = 50.0;  lipo_w = 34.0;  lipo_t = 6.5;   // Li-Pol 603450 1300 мА·ч (измерьте свой!)
tp_l   = 28.0;  tp_w   = 17.0;  tp_pcb = 1.6;   // TP4056 Type-C с защитой
tp_usb_w = 9.0; tp_usb_h = 3.2; tp_usb_out = 1.0;
mt_l   = 36.0;  mt_w   = 17.0;  mt_pcb = 1.6;   // MT3608
mt_h   = 7.0;                                   // полная высота MT3608 с подстроечником
mt_pot = [4.8, 9.5];      // подстроечник (X × Y), синий 3296W
mt_pot_pos = [2.5, 7.0];  // центр подстроечника относительно центра платы MT3608 (измерьте!)
mt_screw_dy = 3.2;        // винт подстроечника смещён от центра корпуса по Y
// Контакты с заводской гребёнкой (ИЗМЕРЬТЕ на своих платах, от центра платы):
tp_pin_far_x = [-6.6, -2.2, 2.2, 6.6];   // OUT-, B-, B+, OUT+ у края без USB
tp_pin_far_y = tp_l/2 - 1.6;
tp_pin_in_x  = [-6.6, 6.6];              // IN-, IN+ у края с USB (не используются)
tp_pin_in_y  = -tp_l/2 + 1.6;
mt_pin_x = 5.5;                          // VIN-/VOUT- на -X, VIN+/VOUT+ на +X
mt_pin_y = mt_l/2 - 2.0;                 // VIN на -Y, VOUT на +Y
tp_cols     = [[0.10, 0.10, 0.10], [0.10, 0.10, 0.10], [0.85, 0.12, 0.10], [0.95, 0.50, 0.10]];
mt_cols_in  = [[0.10, 0.10, 0.10], [0.95, 0.50, 0.10]];
mt_cols_out = [[0.10, 0.10, 0.10], [0.85, 0.12, 0.10]];
sw_l = 8.6;  sw_w = 3.6;  sw_h = 3.5;           // SS12D00, корпус
sw_lever = [1.5, 1.5, 3.0];                     // рычажок (ход ~2 мм вдоль длины)
diode_l = 5.2;  diode_d = 2.7;                  // 1N5819, корпус DO-41

// ---------- Цвета для картинок ----------
c_pcb_esp = [0.12, 0.12, 0.14];
c_pcb_tca = [0.10, 0.30, 0.75];
c_pcb_bno = [0.50, 0.22, 0.68];
c_pcb_p1  = [0.20, 0.55, 0.25];
c_pcb_pwr = [0.10, 0.35, 0.80];
c_gold    = [0.85, 0.70, 0.25];
c_metal   = [0.78, 0.78, 0.80];
c_chip    = [0.08, 0.08, 0.08];
c_hdr     = [0.06, 0.06, 0.06];
c_dupont  = [0.16, 0.16, 0.17];
c_foam    = [0.95, 0.95, 0.90];
// Печатные детали — матовый чёрный PETG; акцент только для надписей
c_print   = [0.14, 0.14, 0.15];
c_print2  = [0.20, 0.20, 0.21];   // крышки чуть светлее, чтобы на картинке читался шов
c_accent  = [0.98, 0.55, 0.12];
c_braid   = [0.07, 0.07, 0.08];   // кабели в чёрной оплётке

// =====================================================================
// Вспомогательные фигуры
// =====================================================================

// Прямоугольник со скруглёнными углами в плане, центр по XY, от z=0 до z=size[2]
module rbox(size, r) {
    rr = max(0.01, min(r, size[0]/2 - 0.01, size[1]/2 - 0.01));
    linear_extrude(size[2])
        offset(r = rr) square([size[0] - 2*rr, size[1] - 2*rr], center = true);
}

// То же, но с фаской снизу (нижняя кромка не режет руку и лучше печатается)
module rbox_chamfer_bottom(size, r, ch) {
    hull() {
        translate([0, 0, 0]) rbox([size[0] - 2*ch, size[1] - 2*ch, 0.01], r - ch);
        translate([0, 0, ch]) rbox([size[0], size[1], size[2] - ch], r);
    }
}

// То же, но с фаской сверху
module rbox_chamfer_top(size, r, ch) {
    hull() {
        rbox([size[0], size[1], size[2] - ch], r);
        translate([0, 0, size[2] - 0.01]) rbox([size[0] - 2*ch, size[1] - 2*ch, 0.01], r - ch);
    }
}

// Паз-«стадион»: отверстие диаметра d, растянутое на ±dx по X (компенсирует
// неточность положения отверстий платы), высота h от z=0
module slot_x(d, dx, h) {
    hull() for (s = [-1, 1]) translate([s*dx, 0, 0]) cylinder(d = d, h = h, $fn = 20);
}

// Защёлка крышки. Язычок свисает вниз от z=0 на высоту h,
// наружная грань язычка в x=0, зуб смотрит наружу (+X).
module snap_tab(w = 7, t = 1.0, h = 5, bump = 0.35) {
    rotate([90, 0, 0])
        linear_extrude(w, center = true)
            polygon([[-t, 0], [-t, -h], [0, -h], [bump, -h + 1.0],
                     [bump, -h + 1.3], [0, -h + 1.7], [0, 0]]);
}

// Ответная выемка в стенке под зуб защёлки (координаты те же, что у snap_tab)
module snap_recess(w = 7, h = 5, bump = 0.35) {
    translate([-0.01, -(w + 0.8)/2, -h + 0.7]) cube([bump + 0.25, w + 0.8, 1.3]);
}

// =====================================================================
// Гребёнка и разъёмы во всех трёх режимах (только для картинок)
// =====================================================================

// Поворот «вверх ногами» вокруг средней плоскости платы: штыри вниз
module flip_pcb(pcb, up) {
    if (up) children();
    else translate([0, 0, pcb]) mirror([0, 0, 1]) children();
}

// Ряд из n штырей вдоль X, центр в (0,0). Низ платы z = 0, толщина платы pcb.
// up = true — планка сверху, штыри вверх; ang — куда загнуты штыри (dupont_bent).
module header_row(n, pcb, up = true, ang = -90, m = conn_mode) {
    L = n*pitch;
    xs = [for (i = [0:n - 1]) -(n - 1)*pitch/2 + i*pitch];
    flip_pcb(pcb, up) {
        if (!m_stub(m)) color(c_hdr) translate([-L/2, -1.25, pcb]) cube([L, 2.5, hdr_spacer]);
        color(c_gold) for (x = xs) translate([x, 0, 0]) {
            if (m_str(m)) translate([-hdr_pin_w/2, -hdr_pin_w/2, -hdr_tail])
                cube([hdr_pin_w, hdr_pin_w, hdr_tail + pcb + hdr_spacer + hdr_pin_up]);
            if (m_bent(m)) {
                translate([-hdr_pin_w/2, -hdr_pin_w/2, -hdr_tail]) cube([hdr_pin_w, hdr_pin_w, hdr_tail + pcb + bent_z + hdr_pin_w/2]);
                rotate([0, 0, ang]) translate([0, -hdr_pin_w/2, pcb + bent_z - hdr_pin_w/2]) cube([hdr_pin_up - 0.6, hdr_pin_w, hdr_pin_w]);
            }
            if (m_stub(m)) translate([-hdr_pin_w/2, -hdr_pin_w/2, -stub_tail]) cube([hdr_pin_w, hdr_pin_w, stub_tail + pcb + stub_len]);
        }
    }
}
// Совместимость: заводская гребёнка в текущем режиме
module header_strip(n, pcb, up = true, ang = -90, m = conn_mode) { header_row(n, pcb, up, ang, m); }

// Провод из верха корпуса: вверх, дуга радиуса dup_bend_r, затем прямо на lead мм.
// Начало в (0,0,0), уходит в сторону угла ang (в плоскости XY, 0° = +X).
module wire_bend(ang, lead, col) {
    color(col) rotate([0, 0, ang]) {
        translate([dup_bend_r, 0, 0]) rotate([90, 0, 0]) rotate([0, 0, 90])
            rotate_extrude(angle = 90, $fn = 24) translate([dup_bend_r, 0]) circle(d = wire_d, $fn = 10);
        if (lead > 0) translate([dup_bend_r, 0, dup_bend_r]) rotate([0, 90, 0]) cylinder(d = wire_d, h = lead, $fn = 10);
    }
}

// Вертикальный корпус Dupont на n контактов вдоль X, центр в (0,0), низ z = 0, верх z = dup_l.
// single = true — n отдельных 1-контактных корпусов; false — один общий (4-pin).
module dupont(n = 1, cols = undef, ang = 0, lead = 3, single = false, wires = true) {
    color(c_dupont)
        if (single) for (i = [0:n - 1])
            translate([-(n - 1)*pitch/2 + i*pitch - dup_w/2 + 0.03, -dup_w/2 + 0.03, 0]) cube([dup_w - 0.06, dup_w - 0.06, dup_l]);
        else translate([-n*pitch/2 + 0.03, -dup_w/2 + 0.03, 0]) cube([n*pitch - 0.06, dup_w - 0.06, dup_l]);
    color([0.30, 0.30, 0.32]) for (i = [0:n - 1])
        translate([-(n - 1)*pitch/2 + i*pitch - 0.6, -dup_w/2 - 0.01, 3]) cube([1.2, 0.2, 4]);
    if (wires) for (i = [0:n - 1])
        translate([-(n - 1)*pitch/2 + i*pitch, 0, dup_l])
            wire_bend(ang, lead, cols == undef ? [0.6, 0.6, 0.6] : cols[i % len(cols)]);
}

// Разъём на ряду из n штырей (координаты как у header_row), в режиме m:
//   straight — вертикальный корпус, провод загибается в сторону ang;
//   bent     — корпус лежит плашмя на загнутых штырях, вдоль ang (ang ⟂ ряду);
//   stubs    — капли припоя на пеньках, провода плашмя в сторону ang.
module conn_on(n, pcb, up = true, cols = undef, ang = 0, lead = 3, single = false, wires = true, m = conn_mode) {
    xs = [for (i = [0:n - 1]) -(n - 1)*pitch/2 + i*pitch];
    function col(i) = cols == undef ? [0.6, 0.6, 0.6] : cols[i % len(cols)];
    flip_pcb(pcb, up) {
        if (m_str(m)) translate([0, 0, pcb + hdr_spacer]) dupont(n, cols, ang, lead, single, wires);
        if (m_bent(m)) {
            color(c_dupont) for (k = single ? [0:n - 1] : [0])
                translate([single ? xs[k] : 0, 0, pcb + bent_z]) rotate([0, 0, ang])
                    translate([bent_gap, -(single ? 1 : n)*pitch/2 + 0.03, -dup_w/2 + 0.03])
                        cube([dup_l, (single ? 1 : n)*pitch - 0.06, dup_w - 0.06]);
            if (wires) for (i = [0:n - 1]) color(col(i)) translate([xs[i], 0, pcb + bent_z]) rotate([0, 0, ang])
                translate([bent_gap + dup_l - 0.01, 0, 0]) rotate([0, 90, 0]) cylinder(d = wire_d, h = lead + bent_lead, $fn = 10);
        }
        if (m_stub(m)) for (i = [0:n - 1]) translate([xs[i], 0, pcb + stub_len*0.55]) {
            color([0.75, 0.75, 0.78]) sphere(d = solder_d, $fn = 12);
            if (wires) color(col(i)) rotate([0, 0, ang]) rotate([0, 90, 0]) cylinder(d = wire_d, h = lead + 2.5, $fn = 10);
        }
    }
}
// Совместимость со старыми вызовами
module dupont_on(n, pcb, up = true, cols = undef, ang = 0, lead = 3, single = false, wires = true, m = conn_mode) {
    conn_on(n, pcb, up, cols, ang, lead, single, wires, m);
}

// Скруглённый «мыльный» корпус: углы в плане радиуса r, нижняя кромка скруглена fb,
// верхняя ft. tb/tt — у кромки, которая лежит на столе принтера, скругление переходит
// в фаску 45° (печатается без поддержек). Центр по XY, от z = 0 до z = size[2].
module soft_corner(r, h, fb, ft, tb, tt) {
    rotate_extrude($fn = 36) intersection() { square([r, h]); hull() {
        square([0.01, h]);
        translate([r - fb, fb]) circle(fb, $fn = 24);
        if (tb) translate([r - 0.586*fb, 0]) square(0.01);
        else translate([r - 0.01, fb]) square(0.01);
        translate([r - ft, h - ft]) circle(ft, $fn = 24);
        if (tt) translate([r - 0.586*ft, h - 0.01]) square(0.01);
    } }
}
module soft_box(size, r, fb = 2, ft = 2, tb = true, tt = true) {
    rr = max(r, fb + 0.01, ft + 0.01);
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(size[0]/2 - rr), sy*(size[1]/2 - rr), 0]) soft_corner(rr, size[2], fb, ft, tb, tt);
}

// =====================================================================
// Болванки плат (только для картинок сборки, в STL не попадают)
// =====================================================================

// Палитра для одиночных проводов внутри пода
c_wire_pal = [[0.85, 0.12, 0.10], [0.10, 0.10, 0.10], [0.15, 0.35, 0.90], [0.95, 0.80, 0.10],
              [0.20, 0.70, 0.25], [0.95, 0.50, 0.10], [0.60, 0.30, 0.75], [0.90, 0.90, 0.90]];

// ESP32-C3 SuperMini: длинная сторона вдоль Y, USB-C на стороне -Y,
// керамическая антенна на стороне +Y, два ряда по 8 штырей вдоль ±X.
// Если смотреть сверху, USB-C внизу (-Y): ряд A (+X) = 5V, G, 3.3, 4, 3, 2, 1, 0
// (от USB к антенне), ряд B (-X) = 5, 6, 7, 8, 9, 10, 20, 21.
// pins_up = false — гребёнка запаяна штырями вниз (как для макетки).
// used_a / used_b — номера штырей (0 = у USB), на которые надеты гнёзда.
// В режиме dupont_bent штыри ряда A загнуты к +X, ряда B — к -X (наружу).
module esp32c3(pins_up = false, used_a = [0, 1, 2, 3], used_b = [0], ang_a = 0, ang_b = 180, lead = 3, wires = true, m = conn_mode) {
    aa = m_bent(m) ? 0 : ang_a;
    ab = m_bent(m) ? 180 : ang_b;
    color(c_pcb_esp) translate([-esp_w/2, -esp_l/2, 0]) cube([esp_w, esp_l, esp_pcb]);
    color(c_metal) translate([-esp_usb_w/2, -esp_l/2 - esp_usb_out, esp_pcb]) cube([esp_usb_w, esp_usb_l, esp_usb_h]);
    color(c_chip) translate([-2.5, 0.5, esp_pcb]) cube([5, 5, 0.9]);
    color(c_metal) for (sx = [-1, 1]) translate([sx*3.6 - 1.2, -3.5, esp_pcb]) cube([2.4, 2.2, 1.4]);
    color([0.85, 0.82, 0.70]) translate([-3, esp_l/2 - 2.6, esp_pcb]) cube([6, 2, 1.1]);
    function py(i) = -(esp_pins - 1)*pitch/2 + i*pitch + esp_pin_y0;
    translate([ esp_row/2, esp_pin_y0, 0]) rotate([0, 0, 90]) header_row(esp_pins, esp_pcb, pins_up, -90, m);
    translate([-esp_row/2, esp_pin_y0, 0]) rotate([0, 0, 90]) header_row(esp_pins, esp_pcb, pins_up,  90, m);
    for (i = used_a) translate([esp_row/2, py(i), 0])
        conn_on(1, esp_pcb, pins_up, [c_wire_pal[i % 8]], aa, lead, true, wires, m);
    for (i = used_b) translate([-esp_row/2, py(i), 0])
        conn_on(1, esp_pcb, pins_up, [c_wire_pal[(i + 4) % 8]], ab, lead, true, wires, m);
}

// TCA9548A: длинная сторона вдоль X, два ряда по 12 контактов вдоль ±Y,
// два крепёжных отверстия у коротких краёв.
// used_n / used_s — номера контактов (0 = у края -X) в рядах +Y и -Y, на которых гнёзда.
// В режиме dupont_bent ряд +Y загнут к +Y, ряд -Y — к -Y (наружу).
module tca9548a(pins_up = false, used_n = [4:11], used_s = [0, 1, 2, 3, 8, 9, 10, 11], ang_n = 90, ang_s = -90, lead = 3, wires = true, m = conn_mode) {
    an = m_bent(m) ? 90 : ang_n;
    as = m_bent(m) ? -90 : ang_s;
    color(c_pcb_tca) difference() {
        translate([-tca_l/2, -tca_w/2, 0]) cube([tca_l, tca_w, tca_pcb]);
        for (sx = [-1, 1]) translate([sx*(tca_l/2 - tca_hole_in), 0, -1]) cylinder(d = tca_hole_d, h = 5, $fn = 16);
    }
    color(c_chip) translate([-4, -3.5, tca_pcb]) cube([8, 7, 1.2]);
    function px(i) = -(tca_pins - 1)*pitch/2 + i*pitch;
    translate([0,  tca_row/2, 0]) header_row(tca_pins, tca_pcb, pins_up,  90, m);
    translate([0, -tca_row/2, 0]) header_row(tca_pins, tca_pcb, pins_up, -90, m);
    for (i = used_n) translate([px(i), tca_row/2, 0])
        conn_on(1, tca_pcb, pins_up, [c_wire_pal[i % 8]], an, lead, true, wires, m);
    for (i = used_s) translate([px(i), -tca_row/2, 0])
        conn_on(1, tca_pcb, pins_up, [c_wire_pal[(i + 3) % 8]], as, lead, true, wires, m);
}

// P1: перфоплата, длинная сторона вдоль X, ряд +Y — 3V3, ряд -Y — GND.
// n_used — сколько гнёзд надето в каждом ряду. pins_up — штыри вверх (как спаяна).
module p1_board(n_used = 8, ang_p = 90, ang_g = -90, lead = 3, wires = true, pins_up = true, m = conn_mode) {
    ap = m_bent(m) ? 90 : ang_p;
    ag = m_bent(m) ? -90 : ang_g;
    color(c_pcb_p1) translate([-p1_l/2, -p1_w/2, 0]) cube([p1_l, p1_w, p1_pcb]);
    function px(i) = -(p1_pins - 1)*pitch/2 + i*pitch;
    translate([0,  p1_row/2, 0]) header_row(p1_pins, p1_pcb, pins_up,  90, m);
    translate([0, -p1_row/2, 0]) header_row(p1_pins, p1_pcb, pins_up, -90, m);
    if (n_used > 0) for (i = [0:n_used - 1]) {
        translate([px(i),  p1_row/2, 0]) conn_on(1, p1_pcb, pins_up, [[0.85, 0.12, 0.10]], ap, lead, true, wires, m);
        translate([px(i), -p1_row/2, 0]) conn_on(1, p1_pcb, pins_up, [[0.10, 0.10, 0.10]], ag, lead, true, wires, m);
    }
    color([0.9, 0.1, 0.1]) translate([-p1_l/2 + 0.4, p1_row/2 - 0.8, p1_pcb]) cube([1.4, 1.6, 0.1]);
    color([0.1, 0.1, 0.1]) translate([-p1_l/2 + 0.4, -p1_row/2 - 0.8, p1_pcb]) cube([1.4, 1.6, 0.1]);
}

// GY-BNO055 (WCMCU-055): край bno_a с рядом контактов — вдоль X на стороне -Y,
// отверстия в углах стороны +Y, чип сверху. Ось X датчика = +Y этой системы.
// hdr — гребёнка штырями вверх (в режиме stubs — пеньки); dup — 4-контактный корпус
// на VCC..LRX (в режиме stubs — 4 припаянных провода); ang — куда идут провода
// (по умолчанию к -Y, от датчика к кисти); bend — куда загнуты штыри в режиме bent
// (-90 — к -Y, за край платы, как в поде; +90 — к +Y, корпус лежит над платой, как на пальце).
module bno055(hdr = true, dup = true, ang = -90, lead = 3, wires = true, m = conn_mode, bend = -90) {
    color(c_pcb_bno) difference() {
        translate([-bno_a/2, -bno_b/2, 0]) cube([bno_a, bno_b, bno_pcb]);
        for (h = bno_holes()) translate([h[0], h[1], -1]) cylinder(d = bno_hole_d, h = 5, $fn = 20);
    }
    color(c_chip) translate([-2.6, -1.0, bno_pcb]) cube([5.2, 3.8, 1.0]);
    // кварц лежит у отверстия, может выступать за край платы
    xs = bno_xtal_side*(bno_a/2 - bno_hole_in - 3.6);
    color(c_metal) translate([xs, bno_b/2 + bno_xtal_out - bno_xtal_l, bno_pcb + bno_xtal_d/2])
        rotate([-90, 0, 0]) cylinder(d = bno_xtal_d, h = bno_xtal_l, $fn = 16);
    // стрелка оси X на шелкографии
    color([0.95, 0.95, 0.95]) translate([-bno_a/2 + 3.2, -2, bno_pcb]) linear_extrude(0.05)
        polygon([[-0.3, 0], [0.3, 0], [0.3, 5], [1.1, 5], [0, 7], [-1.1, 5], [-0.3, 5]]);
    color(c_gold) for (i = [0:bno_npins - 1])
        translate([bno_pin_x(i), bno_row_y(), bno_pcb]) cylinder(d = 1.7, h = 0.05, $fn = 12);
    if (hdr) translate([0, bno_row_y(), 0]) header_row(bno_npins, bno_pcb, true, bend, m);
    if (hdr && dup) translate([bno_hous_x(), bno_row_y(), 0])
        conn_on(4, bno_pcb, true, c_wires4, m_bent(m) ? bend : ang, lead, false, wires, m);
}

// Li-Pol 603450: длинная сторона вдоль Y, выводы на стороне +Y.
module lipo() {
    color([0.80, 0.80, 0.84]) translate([-lipo_w/2, -lipo_l/2, 0]) cube([lipo_w, lipo_l - 4, lipo_t]);
    color([0.95, 0.75, 0.15]) translate([-lipo_w/2, lipo_l/2 - 4, 0.5]) cube([lipo_w, 4, lipo_t - 1]);
    color([0.85, 0.1, 0.1]) translate([-4, lipo_l/2, lipo_t/2]) rotate([-90, 0, 0]) cylinder(d = 1.4, h = 3, $fn = 8);
    color([0.1, 0.1, 0.1]) translate([4, lipo_l/2, lipo_t/2]) rotate([-90, 0, 0]) cylinder(d = 1.4, h = 3, $fn = 8);
}

// TP4056 Type-C: длинная сторона вдоль Y, USB-C на стороне -Y.
// Контакты (заводская гребёнка, одиночные штыри): у края без USB — OUT-, B-, B+, OUT+
// (tp_pin_far_x), у края с USB — IN-, IN+ (не используются, гнёзд на них нет).
// hdr — есть гребёнка; up — штырями вверх; ang — куда уходят провода с OUT/B
// (в режиме bent — +Y, от платы; штыри IN загнуты внутрь, над платой).
module tp4056(hdr = false, up = true, dup = true, ang = 90, lead = 2, wires = true, m = conn_mode) {
    color(c_pcb_pwr) translate([-tp_w/2, -tp_l/2, 0]) cube([tp_w, tp_l, tp_pcb]);
    color(c_metal) translate([-tp_usb_w/2, -tp_l/2 - tp_usb_out, tp_pcb]) cube([tp_usb_w, 7.4, tp_usb_h]);
    color(c_chip) translate([-2.5, 1, tp_pcb]) cube([5, 4, 1.4]);
    color(c_chip) translate([-2, 7, tp_pcb]) cube([4, 3, 1.0]);
    color([0.9, 0.1, 0.1]) translate([-4.5, -5.5, tp_pcb]) cube([1.6, 0.8, 0.6]);  // светодиоды
    color([0.1, 0.3, 0.9]) translate([ 3.0, -5.5, tp_pcb]) cube([1.6, 0.8, 0.6]);
    if (hdr) {
        for (x = tp_pin_far_x) translate([x, tp_pin_far_y, 0]) header_row(1, tp_pcb, up, 90, m);
        for (x = tp_pin_in_x)  translate([x, tp_pin_in_y, 0])  header_row(1, tp_pcb, up, 90, m);
        if (dup) for (i = [0:3]) translate([tp_pin_far_x[i], tp_pin_far_y, 0])
            conn_on(1, tp_pcb, up, [tp_cols[i]], m_bent(m) ? 90 : ang, lead, true, wires, m);
    }
}

// MT3608: длинная сторона вдоль Y, VIN-/VIN+ на стороне -Y, VOUT-/VOUT+ на стороне +Y.
// ang_in / ang_out — куда уходят провода с VIN и VOUT (в режиме bent — наружу: -Y и +Y).
module mt3608(hdr = false, up = true, dup = true, ang_in = 90, ang_out = 90, lead = 2, wires = true, m = conn_mode) {
    color(c_pcb_pwr) translate([-mt_w/2, -mt_l/2, 0]) cube([mt_w, mt_l, mt_pcb]);
    color([0.25, 0.25, 0.27]) translate([-3, -5, mt_pcb]) cylinder(d = 7, h = 4, $fn = 24);  // дроссель
    color(c_chip) translate([2.5, -9, mt_pcb]) cube([3, 3, 1.1]);
    color([0.15, 0.35, 0.85]) translate([mt_pot_pos[0] - mt_pot[0]/2, mt_pot_pos[1] - mt_pot[1]/2, mt_pcb])
        cube([mt_pot[0], mt_pot[1], mt_h - mt_pcb - 0.5]);
    color(c_gold) translate([mt_pot_pos[0], mt_pot_pos[1] + mt_screw_dy, mt_h - 0.5])
        cylinder(d = 2.2, h = 0.5, $fn = 12);
    color(c_gold) for (sy = [-1, 1]) for (sx = [-1, 1])
        translate([sx*mt_pin_x, sy*mt_pin_y, mt_pcb]) cylinder(d = 2.4, h = 0.3, $fn = 12);
    if (hdr) for (sy = [-1, 1]) for (j = [0:1]) {
        sx = j == 0 ? -1 : 1;
        a = m_bent(m) ? sy*90 : (sy < 0 ? ang_in : ang_out);
        translate([sx*mt_pin_x, sy*mt_pin_y, 0]) {
            header_row(1, mt_pcb, up, sy*90, m);
            if (dup) conn_on(1, mt_pcb, up, [sy < 0 ? mt_cols_in[j] : mt_cols_out[j]], a, lead, true, wires, m);
        }
    }
}

// SS12D00: корпус вдоль X, рычажок вверх (+Z), выводы вниз.
module ss12d00() {
    color([0.12, 0.12, 0.12]) translate([-sw_l/2, -sw_w/2, 0]) cube([sw_l, sw_w, sw_h]);
    color([0.20, 0.20, 0.20]) translate([-0.75 + 0.8, -sw_lever[1]/2, sw_h]) cube(sw_lever);
    color(c_metal) for (i = [-1:1]) translate([i*2.54 - 0.3, -0.3, -3.5]) cube([0.6, 0.6, 3.5]);
}

// Диод 1N5819 (DO-41) вдоль X.
module diode1n5819() {
    color(c_chip) rotate([0, 90, 0]) cylinder(d = diode_d, h = diode_l, center = true, $fn = 16);
    color(c_metal) translate([diode_l/2 - 1.2, 0, 0]) rotate([0, 90, 0]) cylinder(d = diode_d + 0.05, h = 0.8, $fn = 16);
    color(c_metal) rotate([0, 90, 0]) cylinder(d = 0.8, h = diode_l + 8, center = true, $fn = 8);
}
