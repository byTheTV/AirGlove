// =====================================================================
// AirGlove — корпус на тыльную сторону кисти («под»): основание + крышка
// (+ «палуба» в режиме dupont_bent).
//
// Внутри: ESP32-C3 SuperMini, TCA9548A, плата питания P1, датчик ладони GY-BNO055.
// Способ подключения — conn_mode из common.scad (можно задать отдельно: pod_mode):
//   dupont_straight — гнёзда стоят вертикально, всё в один этаж, высота ~30 мм;
//   dupont_bent     — штыри загнуты, ~37 гнёзд лежат плашмя и занимают площадь,
//                     поэтому ДВА ЭТАЖА: внизу датчик ладони и P1, сверху на съёмной
//                     «палубе» (pod_deck.stl) ESP32-C3 и TCA9548A;
//   soldered_stubs  — провода припаяны к пенькам, один этаж, самый низкий под.
//
// Система координат (как на руке, ладонь вниз):
//   X — поперёк кисти, -X сторона большого пальца, +X сторона мизинца;
//   Y — вдоль кисти, +Y к пальцам, -Y к запястью;
//   Z — вверх от тыльной стороны кисти; z = 0 — низ основания.
//
// Экспорт (из папки tools/model):
//   openscad -o pod_base.stl -D 'part="base"' pod.scad
//   openscad -o pod_lid.stl  -D 'part="lid"'  pod.scad   (крышка уже перевёрнута для печати)
//   openscad -o pod_deck.stl -D 'part="deck"' pod.scad   (только dupont_bent)
// =====================================================================

include <common.scad>

part = "assembly";   // "assembly" | "open" | "base" | "lid" | "deck" | "lid_in_place" | "electronics"
pod_mode = conn_mode;
inlay = part != "lid";   // заливка логотипа цветом — только на картинках
$fn = 32;

esp_pins_up = false;   // true — гребёнка ESP32-C3 запаяна штырями вверх
tca_pins_up = false;   // true — гребёнка TCA9548A запаяна штырями вверх
p1_pins_up  = true;    // P1 своя перфоплата, штыри вверх

PM   = pod_mode;
deck = m_bent(PM);     // два этажа

// ---------- Стенки ----------
wall    = 1.8;    // толщина стенок
floor_t = 1.6;    // толщина дна
pod_r   = 6.0;    // радиус углов в плане
lid_t   = 2.0;    // толщина крышки
f_bot   = 3.0;    // скругление нижней кромки («как у часов»)
f_top   = 2.5;    // скругление верхней кромки (вся в крышке)
lid_gap = 0.45;   // запас между верхом проводов и крышкой
deck_t  = 1.6;    // палуба (dupont_bent)

// ---------- Гнездо датчика ладони (та же логика допусков, что у держателя на пальце) ----------
seat_clear  = 0.8;   // зазор кармана на сторону (плата 21,0 входит от 19,4 до 22,6)
seat_wall   = 1.6;
seat_floor  = 0.8;   // дно под выемкой хвостов (выемка уходит в дно пода)
seat_tail   = tail_h(PM) + 1.0;   // выемка под хвосты = хвост + 1 мм
seat_xtal   = 0.8;   // выемка под кварц вдоль края с отверстиями
foam_side   = 1.0;   // вспененный скотч 1 мм на стенках кармана — центрует плату
m2_d        = 2.4;
hole_fx     = 1.2;   // паз ±1,2 мм по X под неточность отверстий платы
nut_af      = 4.0;   // гайка M2 (вставляется снизу в паз, потом закрывается липучкой)
nut_h       = 1.6;
foam_dup    = 2.0;   // straight: EVA 2 мм под прижимным ребром крышки (насадка разъёма)

// ---------- Ушки под необязательный ремешок вокруг ладони (20–25 мм) ----------
strap_lugs = true;
strap_w    = 25;
lug_slot   = 2.6;
lug_bar    = 1.8;
lug_h      = 5.0;

// =====================================================================
// Высоты
// =====================================================================
// низ платы над опорой z0: штырями вверх / вниз
function z_up(z0) = z0 + tail_h(PM) + 0.3;
function z_dn(z0) = z0 + (m_str(PM) ? dup_bend_h + dup_l + hdr_spacer
                        : m_bent(PM) ? 0.2 + dup_w/2 + bent_z
                        : conn_h(PM) + 0.3);
function top_up(z, pcb, parts) = z + pcb + max(parts, conn_h(PM) + (m_stub(PM) ? 0.3 : 0));
function top_dn(z, pcb, parts) = z + pcb + max(parts, tail_h(PM));

bno_zp  = seat_floor + seat_tail;                          // низ датчика ладони
bno_top = bno_zp + bno_pcb + (m_str(PM) ? dup_top + dup_bend_h
                             : m_bent(PM) ? conn_h(PM) + 0.3 : max(3.3, conn_h(PM) + 0.3));
p1_z    = p1_pins_up ? z_up(floor_t) : z_dn(floor_t);
p1_top  = p1_pins_up ? top_up(p1_z, p1_pcb, 0) : top_dn(p1_z, p1_pcb, 0);
lvl1_top = max(bno_top, p1_top);
deck_bot = lvl1_top + 0.3;                                  // низ палубы (bent)
deck_top = deck_bot + deck_t;
z_esp0  = deck ? deck_top : floor_t;                        // на что опираются ESP и TCA
esp_z   = esp_pins_up ? z_up(z_esp0) : z_dn(z_esp0);
tca_z   = tca_pins_up ? z_up(z_esp0) : z_dn(z_esp0);
esp_top = esp_pins_up ? top_up(esp_z, esp_pcb, esp_usb_h) : top_dn(esp_z, esp_pcb, esp_usb_h);
tca_top = tca_pins_up ? top_up(tca_z, tca_pcb, tca_parts) : top_dn(tca_z, tca_pcb, tca_parts);
cav_top = max(esp_top, tca_top, p1_top, bno_top) + lid_gap; // низ крышки
pod_h   = cav_top + lid_t;                                  // общая высота

// =====================================================================
// Раскладка в плане
// =====================================================================
seat_px = bno_a/2 + seat_clear;            // полуразмеры кармана датчика (11,3 × 11,05)
seat_py = bno_b/2 + seat_clear;
seat_w  = 2*seat_px + seat_wall;           // гнездо прижато к стенкам +X и -Y
seat_l  = 2*seat_py + seat_wall;
seat_gap = 0.6;                            // зазор от стенки запястья (там край с кварцем)
xtal_wall = 0.8;                           // ниша в стенке запястья под выступающий кварц
cell = conn_run(PM) + 1.27 - 0.0;          // bent: полоса лежачих гнёзд за рядом (от оси ряда)

in_x = deck ? 1.4 + esp_l + 1.5 + tca_l + 0.5
            : 0.5 + esp_w + 1.0 + seat_w;                                   // 43,7
in_y = deck ? 2*(tca_row/2 + conn_run(PM)) + 1.6
            : max(0.4 + esp_l + 2.5 + tca_w + 6.8, seat_gap + seat_l + 1.0 + p1_l + 0.5);
pod_x = in_x + 2*wall;
pod_y = in_y + 2*wall;
in_r  = max(0.5, pod_r - wall);

// ESP: в один этаж — USB-C к запястью (-Y); на палубе — повёрнута, USB-C к большому пальцу (-X)
esp_rot = deck ? -90 : 0;
esp_pos = deck ? [-in_x/2 + 1.4 + esp_l/2, 0, esp_z]
               : [-in_x/2 + 0.5 + esp_w/2, -in_y/2 + 0.4 + esp_l/2, esp_z];
tca_pos = deck ? [in_x/2 - 0.5 - tca_l/2, 0, tca_z]
               : [-in_x/2 + 0.5 + tca_l/2, esp_pos[1] + esp_l/2 + 2.5 + tca_w/2, tca_z];
// датчик ладони повёрнут на 180°: ряд контактов к пальцам (+Y); ось X датчика — к ЗАПЯСТЬЮ
bno_c   = [in_x/2 - seat_px, -in_y/2 + seat_gap + seat_py];
bno_pos = [bno_c[0], bno_c[1], bno_zp];
// P1: в один этаж — вдоль Y у стенки мизинца; в режиме bent — поперёк, у стенки большого пальца
p1_rot  = deck ? 0 : 90;
p1_pos  = deck ? [-in_x/2 + 1.0 + p1_l/2, -in_y/2 + 1.0 + p1_row/2 + conn_run(PM) + 1.3, p1_z]
               : [in_x/2 - 0.5 - p1_w/2, -in_y/2 + seat_gap + seat_l + 1.0 + p1_l/2, p1_z];

function bno_w(p) = [bno_c[0] - p[0], bno_c[1] - p[1]];

// ---------- Прорези для кабелей ----------
// [x, y, угол нормали стенки, ширина, глубина от верха стенки, диаметр кабеля]
cable_d   = 3.0;
pwr_d     = 2.6;
slot_w    = 4.5;
z_cab = m_str(PM) ? cav_top - 3.0 : deck ? deck_top + 2.0 : floor_t + 3.0;   // ось кабеля
slot_dep  = cav_top - z_cab + cable_d/2;
wy = in_y/2 + wall/2;
wx = in_x/2 + wall/2;
pwr_x = deck ? -in_x/2 + 26 : esp_pos[0] + esp_w/2 + 0.5;
slots = [
    [-15, wy,  90, slot_w, slot_dep, cable_d],   // указательный (кан. 2)
    [ -5, wy,  90, slot_w, slot_dep, cable_d],   // средний (кан. 3)
    [  5, wy,  90, slot_w, slot_dep, cable_d],   // безымянный (кан. 4)
    [ 15, wy,  90, slot_w, slot_dep, cable_d],   // мизинец (кан. 5)
    [-wx, in_y/2 - 4.5, 180, slot_w, slot_dep, cable_d],   // большой палец (кан. 1)
    [pwr_x, -wy, 270, 3.4, slot_dep, pwr_d]      // питание 5V/GND от браслета
];

// ---------- USB-C ESP32-C3 ----------
usb_cut_w = 12.5;   // под литой корпус штекера кабеля (измерьте свой кабель)
usb_cut_h = 7.2;
usb_cut_z = esp_z + (esp_pins_up ? esp_pcb + esp_usb_h/2 : esp_pcb + esp_usb_h/2);

// ---------- Защёлки крышки ----------
snap_w = 7; snap_t = 1.0; snap_h = 3.5; snap_bump = 0.35;
snap_clear = 0.2;
snaps = deck ? [[-in_x/2, -17, 180], [-in_x/2, 17, 180], [in_x/2, -17, 0], [in_x/2, 17, 0]]
             : [[-in_x/2, -14, 180], [-in_x/2, 2, 180], [in_x/2, -20, 0], [in_x/2, -12, 0], [16, -in_y/2, 270]];

// =====================================================================

module pod_body() { soft_box([pod_x, pod_y, pod_h], pod_r, f_bot, f_top, true, true); }

module slot_cut(s) {
    translate([s[0], s[1], cav_top]) rotate([0, 0, s[2]])
        translate([-wall, -s[3]/2, -s[4]]) cube([2*wall, s[3], s[4] + 1]);
}
module slot_tooth(s) {
    tooth = s[4] - s[5];
    translate([s[0], s[1], cav_top]) rotate([0, 0, s[2]])
        translate([-wall/2, -(s[3] - 0.3)/2, -tooth]) cube([wall, s[3] - 0.3, tooth + 0.01]);
}

// Гребёнка для кабелей пальцев снаружи стенки пальцев: кабели лежат в выемках
module comb() {
    zb = cav_top - slot_dep;      // низ прорезей
    difference() {
        translate([0, in_y/2 + wall - 0.5, 0]) hull() {
            translate([-21, 0, zb - 3]) cube([42, 4.5, 3]);
            translate([-21, 0, zb - 3 - 4]) cube([42, 0.5, 0.1]);
        }
        for (s = slots) if (s[2] == 90) translate([s[0], in_y/2, zb]) hull() {
            translate([0, 0, 0]) rotate([-90, 0, 0]) cylinder(d = cable_d + 0.4, h = 10, $fn = 20);
            translate([0, 0, 5]) rotate([-90, 0, 0]) cylinder(d = cable_d + 0.4, h = 10, $fn = 20);
        }
    }
}

// Уголки-упоры по углам платы. corners = [(-,-), (+,-), (+,+), (-,+)]
module corner_guides(c, sz, z0, h, corners = [1, 1, 1, 1], cl = 0.3, t = 0.8, a = 2.5) {
    pts = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
    for (i = [0:3]) if (corners[i] == 1) {
        sx = pts[i][0]; sy = pts[i][1];
        px = c[0] + sx*(sz[0]/2 + cl); py = c[1] + sy*(sz[1]/2 + cl);
        translate([0, 0, z0 - 0.01]) {
            translate([min(px, px + sx*t), min(py - sy*a, py + sy*t), 0]) cube([t, a + t, h - z0]);
            translate([min(px - sx*a, px + sx*t), min(py, py + sy*t), 0]) cube([a + t, t, h - z0]);
        }
    }
}

// ---------- Гнездо датчика ладони ----------
module seat_solid() {
    translate([-seat_px - 0.01, -seat_py - seat_wall, floor_t - 0.01])
        cube([2*seat_px + seat_wall + 0.01, 2*seat_py + seat_wall + 0.01, bno_zp + bno_pcb + 0.7 - floor_t]);
}
module seat_cuts() {
    translate([-seat_px, -seat_py, bno_zp]) cube([2*seat_px, 2*seat_py, 10]);
    translate([-seat_px + 0.9, -seat_py, seat_floor]) cube([2*seat_px - 1.8, seat_py - 7.3, seat_tail + 1]);
    translate([-seat_px + 0.9, bno_b/2 - 7.5, bno_zp - seat_xtal]) cube([2*seat_px - 1.8, seat_py - bno_b/2 + 7.5, seat_xtal + 1]);
    translate([-seat_px + 1, seat_py - 0.01, bno_zp + 1.0]) cube([2*seat_px - 2, seat_gap + xtal_wall + 0.01, 4.0]);
    for (h = bno_holes()) {
        translate([h[0], h[1], -1]) slot_x(m2_d, hole_fx, bno_zp + 2);
        translate([h[0] - hole_fx - nut_af*0.578, h[1] - (nut_af + 0.2)/2, -1])
            cube([2*(hole_fx + nut_af*0.578), nut_af + 0.2, nut_h + 0.2 + 1]);
    }
}

// ---------- Опоры плат (в локальной системе платы) ----------
module esp_supports(z0) {
    if (esp_pins_up) {
        for (sx = [-1, 1]) translate([sx*4 - 1, -esp_l/2 + 2, z0 - 0.01]) cube([2, esp_l - 4, esp_z - z0 + 0.01]);
    } else {
        for (sx = [-1, 1]) translate([sx*3.0 - 0.6, -esp_l/2 + 1.5, z0 - 0.01]) cube([1.2, esp_l - 3, esp_z - z0 + 0.01]);
        translate([-3.6, -0.6, z0 - 0.01]) cube([7.2, 1.2, min(6, esp_z - z0)]);
    }
}
module tca_supports(z0) {
    for (sx = [-1, 1]) translate([sx*(tca_l/2 - tca_hole_in), 0, z0 - 0.01]) {
        cylinder(d = 5.0, h = tca_z - z0 + 0.01);
        cylinder(d = tca_hole_d - 0.4, h = tca_z - z0 + tca_pcb + 0.8);
    }
}
module p1_supports(z0) {
    for (sx = [-1, 1]) translate([sx*(p1_l/2 - 1.0) - 1.0, -p1_w/2 + 0.5, z0 - 0.01])
        cube([2.0, p1_w - 1, p1_z - z0 + 0.01]);
    corner_guides([0, 0], [p1_l, p1_w], p1_z + 1.2, p1_z + 1.2, [1, 0, 0, 1]);
}

module interior_features() {
    if (!deck) {
        translate([esp_pos[0], esp_pos[1], 0]) rotate([0, 0, esp_rot]) esp_supports(floor_t);
        translate([tca_pos[0], tca_pos[1], 0]) tca_supports(floor_t);
    } else {
        // полки под палубу вдоль стенок ±X (снизу скос 45°)
        for (sx = [-1, 1]) translate([sx*in_x/2, 0, 0]) mirror([sx < 0 ? 1 : 0, 0, 0])
            translate([0, -(in_y/2 - 8), deck_bot]) rotate([-90, 0, 0]) linear_extrude(in_y - 16)
                polygon([[0.01, 0], [-2.0, 0], [-2.0, 0.01], [0.01, 2.0]]);
    }
    translate([p1_pos[0], p1_pos[1], 0]) rotate([0, 0, p1_rot]) p1_supports(floor_t);
    translate([bno_c[0], bno_c[1], 0]) rotate([0, 0, 180]) seat_solid();
}

module lugs() {
    if (strap_lugs) translate([0, 0, 0]) soft_box([pod_x + 2*(lug_slot + lug_bar), strap_w + 5, lug_h], 2.5, 1.0, 1.5, true, false);
}
module lug_slots() {
    if (strap_lugs) for (sx = [-1, 1])
        translate([sx > 0 ? pod_x/2 : -pod_x/2 - lug_slot, -(strap_w + 1)/2, -1]) cube([lug_slot, strap_w + 1, lug_h + 2]);
}

module usb_cut() {
    if (deck) translate([-pod_x/2 - 1, esp_pos[1], usb_cut_z]) {
        rotate([0, 90, 0]) linear_extrude(wall + 2) offset(r = 2) square([usb_cut_h - 4, usb_cut_w - 4], center = true);
        translate([0, -usb_cut_w/2, 0]) cube([wall + 2, usb_cut_w, 30]);
    } else translate([esp_pos[0], -pod_y/2 - 1, usb_cut_z]) {
        rotate([-90, 0, 0]) linear_extrude(wall + 2) offset(r = 2) square([usb_cut_w - 4, usb_cut_h - 4], center = true);
        translate([-usb_cut_w/2, 0, 0]) cube([usb_cut_w, wall + 2, 30]);
    }
}

module pod_base() {
    color(c_print) difference() {
        union() {
            difference() {
                union() {
                    intersection() { pod_body(); translate([-100, -100, -1]) cube([200, 200, cav_top + 1]); }
                    lugs();
                }
                translate([0, 0, floor_t]) rbox([in_x, in_y, cav_top], in_r);
            }
            interior_features();
            comb();
        }
        for (s = slots) slot_cut(s);
        usb_cut();
        for (s = snaps) translate([s[0], s[1], cav_top]) rotate([0, 0, s[2]]) snap_recess(snap_w, snap_h, snap_bump);
        translate([bno_c[0], bno_c[1], 0]) rotate([0, 0, 180]) seat_cuts();
        lug_slots();
    }
}

// Палуба (dupont_bent): лежит на полках, на ней ESP32-C3 и TCA9548A; прорези у торцов — провода вниз
module pod_deck() {
    if (deck) color(c_print2) difference() {
        union() {
            translate([0, 0, deck_bot]) rbox([in_x - 0.6, in_y - 0.6, deck_t], in_r - 0.3);
            translate([esp_pos[0], esp_pos[1], 0]) rotate([0, 0, esp_rot]) esp_supports(deck_top);
            translate([tca_pos[0], tca_pos[1], 0]) tca_supports(deck_top);
        }
        // прорези для проводов к нижнему этажу (у торцов ±Y) и окно над датчиком ладони
        for (sy = [-1, 1]) translate([-in_x/2 + 3, sy*(in_y/2 - 3.2) - 1.75, deck_bot - 1]) cube([in_x - 6, 3.5, deck_t + 2]);
    }
}

// Крышка в рабочем положении
module pod_lid() {
    usb_top = usb_cut_z + usb_cut_h/2;
    color(c_print2) {
        difference() {
            intersection() { pod_body(); translate([-100, -100, cav_top]) cube([200, 200, 50]); }
            if (usb_top > cav_top - 0.01) usb_cut();
            translate([0, 0, -0.5]) pod_logo(1);
        }
        for (s = snaps) translate([s[0], s[1], cav_top]) rotate([0, 0, s[2]])
            translate([-snap_clear, 0, 0]) snap_tab(snap_w, snap_t, snap_h, snap_bump);
        for (s = slots) slot_tooth(s);
        // зуб над USB-C
        if (usb_top < cav_top) {
            if (deck) translate([-pod_x/2 + 0.3, esp_pos[1] - (usb_cut_w - 0.3)/2, usb_top]) cube([wall, usb_cut_w - 0.3, cav_top - usb_top + 0.01]);
            else translate([esp_pos[0] - (usb_cut_w - 0.3)/2, -pod_y/2 + 0.3, usb_top]) cube([usb_cut_w - 0.3, wall, cav_top - usb_top + 0.01]);
        }
        // straight: прижимное ребро над насадкой разъёма датчика ладони (через EVA 2 мм)
        if (m_str(PM)) {
            hz = bno_zp + bno_pcb + dup_top + 0.8 + 1.4;
            rc = bno_w([bno_hous_x(), bno_row_y() + 2.1]);
            translate([rc[0] - 6.5, rc[1] - 0.9, hz]) cube([min(13, in_x/2 - 0.3 - rc[0] + 6.5), 1.8, cav_top - hz + 0.01]);
        }
        // прижимы плат, стоящих штырями вниз (не дают им подняться)
        if (!esp_pins_up) translate([esp_pos[0], esp_pos[1], 0]) rotate([0, 0, esp_rot]) for (sx = [-1, 1])
            translate([sx*5.0, esp_l/2 - 2.0, esp_z + esp_pcb + 0.3]) cylinder(d = 2.4, h = cav_top - esp_z - esp_pcb - 0.3 + 0.01);
        if (!tca_pins_up) for (sx = [-1, 1])
            translate([tca_pos[0] + sx*(tca_l/2 - tca_hole_in), tca_pos[1], tca_z + tca_pcb + 0.2]) difference() {
                cylinder(d = 5.0, h = cav_top - tca_z - tca_pcb - 0.2 + 0.01);
                translate([0, 0, -0.01]) cylinder(d = tca_hole_d, h = 1.2);
            }
    }
    // логотип углублён на 0,5 мм (крышка печатается верхом на столе); на картинке — заливка
    if (inlay) color(c_accent) translate([0, 0, -0.5]) pod_logo(0.49);
}
module pod_logo(h) {
    translate([0, deck ? -6 : -12, pod_h - 0.01]) linear_extrude(h + 0.02)
        text("AirGlove", size = 6, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
}

// Платы на своих местах (для картинок)
module pod_electronics(wires = true) {
    translate(esp_pos) rotate([0, 0, esp_rot]) esp32c3(esp_pins_up, [0, 1, 2, 3], [0], 90, 90, 2, wires, PM);
    translate(tca_pos) tca9548a(tca_pins_up, [4:11], [0, 1, 2, 3, 8, 9, 10, 11], 90, -90, 2, wires, PM);
    translate(p1_pos) rotate([0, 0, p1_rot]) p1_board(8, deck ? 90 : 0, deck ? -90 : 0, 2, wires, p1_pins_up, PM);
    translate([bno_c[0], bno_c[1], 0]) rotate([0, 0, 180]) {
        translate([0, 0, bno_zp]) bno055(true, true, -90, 3, wires, PM);
        if (m_str(PM)) color(c_print) translate([bno_hous_x(), bno_row_y(), bno_zp + bno_pcb + dup_top])
            difference() {
                translate([-6.4, -2.35, -5]) cube([12.8, 4.7, 5.8]);
                translate([-5.25, -1.45, -6]) cube([10.5, 2.9, 6]);
                translate([-4.6, -3, -0.5]) cube([9.2, 3 + 0.7, 2]);
            }
        for (h = bno_holes()) {
            color(c_metal) translate([h[0], h[1], bno_zp + bno_pcb]) cylinder(d = 3.8, h = 1.3, $fn = 20);
            color(c_metal) translate([h[0], h[1], 0.1]) cylinder(d = nut_af/cos(30), h = nut_h, $fn = 6);
        }
        color(c_foam) for (sx = [-1, 1]) translate([sx*(seat_px - foam_side/2) - foam_side/2, -6, bno_zp]) cube([foam_side, 12, 1.5]);
    }
}

// Данные для сборки (assembly.scad подключает этот файл через use <...>)
function pod_dims()   = [pod_x, pod_y, pod_h, cav_top];
function pod_slots()  = slots;
function pod_has_deck() = deck;
function pod_bno_screws() = [for (h = bno_holes()) let(w = bno_w(h)) [w[0], w[1], bno_zp + bno_pcb]];

module pod_lid_print() { translate([0, 0, pod_h]) rotate([180, 0, 0]) pod_lid(); }
module pod_deck_print() { translate([0, 0, -deck_bot]) pod_deck(); }

echo(str("POD [", PM, "]: ", pod_x, " x ", pod_y, " x ", pod_h, " мм (внутри ", in_x, " x ", in_y, ", низ крышки ", cav_top,
         "; верх: ESP ", esp_top, ", TCA ", tca_top, ", P1 ", p1_top, ", BNO ", bno_top,
         deck ? str("; палуба ", deck_bot, "…", deck_top) : "", ")"));

if (part == "base") pod_base();
else if (part == "lid") pod_lid_print();
else if (part == "deck") pod_deck_print();
else if (part == "lid_in_place") pod_lid();
else if (part == "electronics") pod_electronics();
else if (part == "open") { pod_base(); pod_deck(); pod_electronics(); }
else { pod_base(); pod_deck(); pod_electronics(); %pod_lid(); }
