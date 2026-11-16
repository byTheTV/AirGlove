// =====================================================================
// AirGlove — коробка питания на браслете (предплечье, выше манжеты перчатки).
//
// Внутри: Li-Pol 603450 1300 мА·ч (50×34×6,5), TP4056 Type-C, MT3608, тумблер SS12D00,
// диод 1N5819 (в термоусадке на проводе). У TP4056 и MT3608 ЗАВОДСКАЯ гребёнка 2,54 мм,
// ничего не выпаиваем. Используются: TP4056 — B+, B-, OUT+, OUT- (IN± свободны);
// MT3608 — VIN+, VIN-, VOUT+, VOUT-.
//
// Раскладка зависит от способа подключения (wb_mode = conn_mode):
//   dupont_straight — над (или под) рядом штырей столбик 2,5 + 14 мм + изгиб провода,
//       поэтому АККУМУЛЯТОР РЯДОМ с модулями (вдоль руки): модули у локтя, аккумулятор
//       к кисти. Так коробка работает и при штырях вверх, и при штырях вниз;
//   dupont_bent / soldered_stubs — модули низкие, два «этажа»: аккумулятор внизу,
//       модули над ним на прокладках из EVA (хвосты штырей не давят на аккумулятор).
// Ориентация гребёнок: tp_pins_up / mt_pins_up (по умолчанию штырями ВВЕРХ).
//
// Система координат: X — поперёк предплечья, Y — вдоль (+Y к кисти, -Y к локтю),
// Z — вверх; z = 0 — низ дна по центру.
//
// Экспорт:
//   openscad -o wrist_box.stl     -D 'part="base"' wrist_box.scad
//   openscad -o wrist_box_lid.stl -D 'part="lid"'  wrist_box.scad  (крышка перевёрнута для печати)
// =====================================================================

include <common.scad>

part = "assembly";   // "assembly" | "open" | "base" | "lid" | "lid_in_place" | "electronics" | "exploded"
wb_mode = conn_mode;
inlay = part != "lid";   // заливка надписей цветом — только на картинках
$fn = 32;

// ---------- Гребёнки на модулях ----------
wb_headers = true;   // true — у TP4056 и MT3608 заводская гребёнка (так у нас); false — только площадки
tp_pins_up = true;   // гребёнка TP4056 штырями вверх (false — вниз)
mt_pins_up = true;   // гребёнка MT3608 штырями вверх (false — вниз)

WM = wb_headers ? wb_mode : "soldered_stubs";
bat_under = !m_str(WM);      // два этажа: аккумулятор под модулями

// ---------- Стенки ----------
wb_wall  = 1.6;
wb_floor = 1.6;
wb_lid_t = 1.6;
wb_r     = 5.6;      // радиус углов в плане (снаружи)
wb_f_bot = 3.0;      // скругление нижней кромки
wb_f_top = 2.0;      // скругление верхней кромки (почти вся в крышке)
wb_clear = 0.45;     // зазор над самым высоким (провода/корпуса) до крышки
foam     = 0.8;      // вспененный скотч
bat_gap  = 3.5;      // straight: между модулями и аккумулятором (выводы аккумулятора)
bat_pocket_h = lipo_t + 0.5;
bat_top  = wb_floor + bat_pocket_h;          // верх отсека аккумулятора (8,6)

// ---------- Высоты модулей ----------
function ph(up, z0) = z0 + (up ? tail_h(WM) + 0.3
                             : m_str(WM) ? dup_top + dup_bend_h + 0.2
                             : m_bent(WM) ? 0.2 + dup_w/2 + bent_z
                             : conn_h(WM) + 0.3);
z_mod0 = bat_under ? bat_top : wb_floor;     // на что опираются модули
tp_z = ph(tp_pins_up, z_mod0);
mt_z = ph(mt_pins_up, z_mod0);
function mod_top(z, pcb, parts, up) = z + pcb + (up ? max(parts, conn_h(WM)) : max(parts, tail_h(WM)));
tp_top = mod_top(tp_z, tp_pcb, tp_usb_h, tp_pins_up);
mt_top = mod_top(mt_z, mt_pcb, mt_h - mt_pcb, mt_pins_up);

// ---------- План ----------
wb_in_x = max(lipo_w + 2.4, 0.5 + tp_w + 1.4 + mt_w + 0.5);       // 36,4
tp_len  = tp_usb_out + 0.2 + tp_l;                                 // от стенки -Y до дальнего края TP
mt_y0   = m_bent(WM) ? 0.5 + mt_pin_y + conn_run(WM) : m_stub(WM) ? 0.5 + 2.5 + mt_l/2 : 0.5 + mt_l/2;
mod_len = max(tp_len, mt_y0 + mt_l/2 + (m_bent(WM) ? conn_run(WM) - 2 : m_stub(WM) ? 2.5 : 0));
wb_in_y = bat_under ? max(mod_len + 0.5, lipo_l + 2.0, m_bent(WM) ? 2*mt_y0 : 0)
                    : max(tp_len, 0.5 + mt_l) + bat_gap + lipo_l + 1.0;
wb_in   = [wb_in_x, wb_in_y];
wb_out  = [wb_in_x + 2*wb_wall, wb_in_y + 2*wb_wall];
Y0 = -wb_in_y/2;

tp_x  = -wb_in_x/2 + 0.5 + tp_w/2;
mt_x  =  wb_in_x/2 - 0.5 - mt_w/2;
tp_yc = Y0 + tp_usb_out + 0.2 + tp_l/2;
mt_yc = Y0 + mt_y0;
tp_pos = [tp_x, tp_yc, tp_z];
mt_pos = [mt_x, mt_yc, mt_z];
bat_y  = bat_under ? 0 : Y0 + max(tp_len, 0.5 + mt_l) + bat_gap + lipo_l/2;
bat_pos = [0, bat_y, wb_floor];
// в режиме straight выводы аккумулятора смотрят к модулям (-Y), иначе — к кисти (+Y)
bat_rot = bat_under ? 0 : 180;

// Тумблер SS12D00 на стенке -X (рычажок наружу), над аккумулятором
sw_y = bat_under ? (m_bent(WM) ? Y0 + tp_len + 18.0 : Y0 + tp_len + 9.0) : bat_y + 5;
sw_z = bat_top + 5.0;
diode_pos = bat_under ? [-8, Y0 + wb_in_y - 6, bat_top + 4.5] : [6, bat_y + 12, bat_top + 4.5];

// Подстроечник MT3608: винт и окошки светодиодов TP4056
pot_xy  = [mt_x + mt_pot_pos[0], mt_yc + mt_pot_pos[1] + mt_screw_dy];
pot_top = mt_z + mt_h;
pot_hole_d = 4.0;     // под отвёртку 2–3 мм; трубка-направляющая от крышки до подстроечника
led_xy  = [[tp_x - 3.7, tp_yc - 5.1], [tp_x + 3.8, tp_yc - 5.1]];
led_top = tp_z + tp_pcb + 0.6;
led_hole_d = 2.5;

// ---------- Вырезы ----------
usb_w  = 12.5;   // под литой штекер USB-C (измерьте свой кабель)
usb_h  = 7.2;
usb_zc = tp_z + tp_pcb + tp_usb_h/2;
pwr_slot = [4, 3.4, 4.5, 2.6];   // [x, ширина, глубина от верха стенки, диаметр кабеля] в стенке +Y

// ---------- Высота коробки ----------
wb_top = max(tp_top, mt_top, usb_zc + usb_h/2 + 0.6, sw_z + sw_w/2 + 1.0, bat_top + 6) + wb_clear;
wb_h   = wb_top + wb_lid_t;

// ---------- Ушки под ремешок 25 мм ----------
wb_strap_w  = 25;
wb_lug_slot = 3.0;    // ремешок-липучка толще, чем стропа
wb_lug_bar  = 2.0;
wb_lug_h    = 6.0;

// ---------- Защёлки ----------
snap_w = 7; snap_t = 1.0; snap_h = 4; snap_bump = 0.35; snap_clear = 0.2;
wb_snaps = m_str(WM) ? [[-wb_in_x/2, -28, 180], [-wb_in_x/2, 2, 180], [-wb_in_x/2, 37, 180],
                        [ wb_in_x/2, -27,   0], [ wb_in_x/2, 2,   0], [ wb_in_x/2, 37,   0]]
    : m_bent(WM)     ? [[-wb_in_x/2, Y0 + 12, 180], [-wb_in_x/2, -Y0 - 5, 180],
                        [ wb_in_x/2, Y0 + 12,   0], [ wb_in_x/2, 0, 0], [ wb_in_x/2, -Y0 - 12, 0]]
    :                  [[-wb_in_x/2, Y0 + 12, 180], [-wb_in_x/2, -Y0 - 5, 180],
                        [ wb_in_x/2, Y0 + 12,   0], [ wb_in_x/2, -Y0 - 12, 0]];

// Проверки
assert(wb_in_x >= lipo_w + 1.0 && wb_in_y >= lipo_l + 2.0, "Аккумулятор не влезает: увеличьте wb_in");
assert(wb_top >= max(tp_top, mt_top) + 0.3, "Крышка задевает корпуса Dupont");
echo(str("WRIST BOX [", WM, bat_under ? ", АКБ под модулями" : ", АКБ рядом с модулями",
         ", TP ", tp_pins_up ? "вверх" : "вниз", ", MT ", mt_pins_up ? "вверх" : "вниз", "]: ",
         wb_out[0], " x ", wb_out[1], " x ", wb_h, " мм (с ушками ", wb_out[0] + 2*(wb_lug_slot + wb_lug_bar),
         "); внутри ", wb_in_x, " x ", wb_in_y, "; низ плат TP ", tp_z, " / MT ", mt_z,
         "; верх TP ", tp_top, " / MT ", mt_top, "; низ крышки ", wb_top));

// =====================================================================

module wb_body() { soft_box([wb_out[0], wb_out[1], wb_h], wb_r, wb_f_bot, wb_f_top, true, true); }

module wb_lugs() {
    soft_box([wb_out[0] + 2*(wb_lug_slot + wb_lug_bar), wb_strap_w + 5, wb_lug_h], 2.5, 1.0, 1.5, true, false);
}
module wb_lug_slots() {
    for (sx = [-1, 1])
        translate([sx > 0 ? wb_out[0]/2 : -wb_out[0]/2 - wb_lug_slot, -(wb_strap_w + 1)/2, -10])
            cube([wb_lug_slot, wb_strap_w + 1, 30]);
}

// Держатель тумблера: две «щёчки» от стенки -X с полочками; низ скошен под 45°
module switch_holder() {
    for (sy = [-1, 1]) {
        yc = sw_y + sy*(sw_l/2 + 0.15 + 0.6);
        translate([0, yc + 0.6, 0]) rotate([90, 0, 0]) linear_extrude(1.2)
            polygon([[-wb_in_x/2 - 0.01, bat_top + 0.2],
                     [-wb_in_x/2 + 2.2, sw_z - sw_w/2 - 0.6],
                     [-wb_in_x/2 + 3.8, sw_z - sw_w/2 - 0.6],
                     [-wb_in_x/2 + 3.8, sw_z + sw_w/2],
                     [-wb_in_x/2 - 0.01, sw_z + sw_w/2]]);
        translate([-wb_in_x/2, sy > 0 ? yc - 0.6 - 0.8 : yc + 0.6, sw_z - sw_w/2 - 0.6]) cube([3.8, 0.8, 0.6]);
    }
}

// Пьедесталы под модули (только straight: модули стоят на дне рядом с аккумулятором).
// Короткие — сплошные, высокие (штырями вниз) — рамкой 1,2 мм. Вспененный скотч сверху.
module wb_pedestal(c, sz, top) {
    h = top - foam - wb_floor;
    if (h > 0.3) translate([c[0], c[1], wb_floor - 0.01]) difference() {
        rbox([sz[0], sz[1], h + 0.01], 1.5);
        if (h > 4) translate([0, 0, -1]) rbox([sz[0] - 2.4, sz[1] - 2.4, h + 2], 0.5);
    }
}
tp_ped = [[tp_x, tp_yc - 2.5], [12, 12]];
mt_ped = [[mt_x, mt_yc], [12, 14]];

module wrist_box_base() {
    color(c_print) difference() {
        union() {
            difference() {
                union() {
                    intersection() { wb_body(); translate([-100, -100, -1]) cube([200, 200, wb_top + 1]); }
                    wb_lugs();
                }
                translate([0, 0, wb_floor]) rbox([wb_in_x, wb_in_y, wb_top], wb_r - wb_wall);
            }
            switch_holder();
            if (!bat_under) {
                wb_pedestal(tp_ped[0], tp_ped[1], tp_z);
                wb_pedestal(mt_ped[0], mt_ped[1], mt_z);
                // упоры аккумулятора со стороны модулей (выводы проходят между ними)
                for (sx = [-1, 1]) translate([sx*12 - 2, bat_y - lipo_l/2 - 1.6, wb_floor - 0.01]) cube([4, 1.2, 4]);
            }
        }
        // USB-C TP4056 — паз сверху, сверху его закрывает зуб крышки
        translate([tp_x, -wb_out[1]/2 - 1, usb_zc]) rotate([-90, 0, 0])
            linear_extrude(wb_wall + 2) offset(r = 2) square([usb_w - 4, usb_h - 4], center = true);
        translate([tp_x - usb_w/2, -wb_out[1]/2 - 1, usb_zc]) cube([usb_w, wb_wall + 2, 40]);
        // рычажок тумблера
        translate([-wb_out[0]/2 - 1, sw_y - 2.6, sw_z - 1.2]) cube([wb_wall + 2, 5.2, 2.4]);
        // прорезь кабеля 5V/GND к поду
        translate([pwr_slot[0] - pwr_slot[1]/2, wb_in_y/2 - 1, wb_top - pwr_slot[2]])
            cube([pwr_slot[1], wb_wall + 2, pwr_slot[2] + 1]);
        for (s = wb_snaps) translate([s[0], s[1], wb_top]) rotate([0, 0, s[2]]) snap_recess(snap_w, snap_h, snap_bump);
        wb_lug_slots();
    }
}

// Трубка от крышки вниз: направляет отвёртку к подстроечнику / свет светодиода
module lid_tube(xy, d_in, d_out, z_bot) {
    if (wb_top - z_bot > 1.0) translate([xy[0], xy[1], z_bot]) difference() {
        cylinder(d = d_out, h = wb_top - z_bot + 0.01);
        translate([0, 0, -1]) cylinder(d = d_in, h = wb_top);
    }
}

module wrist_box_lid() {
    color(c_print2) {
        difference() {
            intersection() { wb_body(); translate([-100, -100, wb_top]) cube([200, 200, 50]); }
            translate([pot_xy[0], pot_xy[1], wb_top - 1]) cylinder(d = pot_hole_d, h = 5);
            for (p = led_xy) translate([p[0], p[1], wb_top - 1]) cylinder(d = led_hole_d, h = 5);
            translate([0, 0, -0.5]) lid_text(1);
        }
        for (s = wb_snaps) translate([s[0], s[1], wb_top]) rotate([0, 0, s[2]])
            translate([-snap_clear, 0, 0]) snap_tab(snap_w, snap_t, snap_h, snap_bump);
        // зуб над USB-C
        translate([tp_x - (usb_w - 0.3)/2, -wb_out[1]/2 + 0.3, usb_zc + usb_h/2])
            cube([usb_w - 0.3, wb_wall - 0.3, wb_top - usb_zc - usb_h/2 + 0.01]);
        // зуб-прижим кабеля питания
        translate([pwr_slot[0] - (pwr_slot[1] - 0.3)/2, wb_in_y/2, wb_top - (pwr_slot[2] - pwr_slot[3])])
            cube([pwr_slot[1] - 0.3, wb_wall - 0.3, pwr_slot[2] - pwr_slot[3] + 0.01]);
        lid_tube(pot_xy, pot_hole_d, pot_hole_d + 2.4, pot_top + 1.5);
        for (p = led_xy) lid_tube(p, led_hole_d, led_hole_d + 2.0, led_top + 2.5);
    }
    // надписи углублены на 0,5 мм (крышка печатается верхом на столе); на картинке — заливка
    if (inlay) color(c_accent) translate([0, 0, -0.5]) lid_text(0.49);
}
module lid_text(h) {
    translate([pot_xy[0], pot_xy[1] - 6.5, wb_h - 0.01]) linear_extrude(h + 0.02)
        text("5V", size = 3.5, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
    translate([bat_under ? -4 : 0, bat_under ? 8 : bat_y + 4, wb_h - 0.01]) rotate([0, 0, 90]) linear_extrude(h + 0.02)
        text("AirGlove", size = 5, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
}

module wrist_box_electronics(wires = true) {
    translate(bat_pos) rotate([0, 0, bat_rot]) lipo();
    // пена / EVA под модулями
    color(c_foam) for (p = [[tp_x, tp_yc - 2.5, tp_z], [mt_x, mt_yc, mt_z]])
        translate([p[0], p[1], bat_under ? bat_top : p[2] - foam]) rbox([10, 12, bat_under ? p[2] - bat_top : foam], 1);
    translate(tp_pos) tp4056(wb_headers, tp_pins_up, true, tp_pins_up ? 90 : -90, 2, wires, WM);
    translate(mt_pos) mt3608(wb_headers, mt_pins_up, true, 90, mt_pins_up ? 90 : -90, 2, wires, WM);
    translate([-wb_in_x/2 + sw_h + 0.1, sw_y, sw_z]) rotate([0, -90, 0]) rotate([0, 0, 90]) ss12d00();
    translate(diode_pos) diode1n5819();
}

// Данные для сборки
function wb_dims() = [wb_out[0], wb_out[1], wb_h];
function wb_lug_x() = wb_out[0]/2 + wb_lug_slot/2;
function wb_pwr_exit() = [pwr_slot[0], wb_out[1]/2, wb_top - pwr_slot[2] + pwr_slot[3]/2];

module wrist_box_lid_print() {
    translate([0, 0, wb_h]) rotate([180, 0, 0]) wrist_box_lid();
}

if (part == "base") wrist_box_base();
else if (part == "lid") wrist_box_lid_print();
else if (part == "lid_in_place") wrist_box_lid();
else if (part == "electronics") wrist_box_electronics();
else if (part == "open") { wrist_box_base(); wrist_box_electronics(); }
else if (part == "exploded") { wrist_box_base(); wrist_box_electronics(); translate([0, 0, 30]) wrist_box_lid(); }
else { wrist_box_base(); wrist_box_electronics(); %wrist_box_lid(); }
