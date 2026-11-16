// =====================================================================
// AirGlove — сборка для картинок: правая рука, перчатка без пальцев,
// под на тыле кисти, 5 держателей датчиков НА КОНЧИКАХ пальцев (ногтевые фаланги),
// коробка питания на браслете, кабели с запасом-петлями над суставами DIP, PIP и MCP.
//
// Только для визуализации (печатаются отдельные файлы pod / finger_mount / wrist_box).
//
//   view = "assembly"  — рука в сборе (по умолчанию)
//   view = "closeup"   — держатель на кончике пальца крупно (крышка разрезана по оси);
//                        крепление — как задано tip_style (лента или напалок из TPU)
//   view = "wrist_exploded" — коробка питания: модули, гнёзда, аккумулятор, крышка поднята
//   view = "collide"   — пересечение держателей пальцев ci и cj (пусто — не касаются)
//                        с зазором gap; spread — насколько разведены пальцы
//   explode = true     — разнесённый вид пода (основание, платы, палуба, крышка)
// Способ подключения задаётся так: -D 'conn_mode="dupont_bent"' (см. common.scad).
//
// Система координат: правая рука ладонью вниз, X поперёк (большой палец в -X),
// Y вдоль руки (+Y к пальцам, y = 0 — складка запястья), Z вверх (тыльная сторона).
// =====================================================================

include <common.scad>
use <pod.scad>
use <finger_mount.scad>
use <wrist_box.scad>

view    = "assembly";
explode = false;
spread  = 1.0;      // 1 — пальцы разведены (как на картинках), 0 — сведены вместе
ci = 0; cj = 1;     // view = "collide": какие держатели проверять (индексы в fingers)
gap = 0;            // view = "collide": требуемый зазор между держателями, мм
$fn = 28;

// ---------- Цвета ----------
c_skin  = [0.93, 0.76, 0.64];
c_glove = [0.40, 0.41, 0.44];
c_cuff  = [0.30, 0.31, 0.34];
c_velcro = [0.45, 0.45, 0.47];
c_ring  = [0.10, 0.10, 0.11];
c_cable = c_braid;
c_power = c_braid;
c_strap = [0.10, 0.10, 0.11];
c_mount = c_print;
c_cover = c_print2;

// ---------- Матрицы поворота ----------
function rx(a) = [[1, 0, 0], [0, cos(a), -sin(a)], [0, sin(a), cos(a)]];
function ry(a) = [[cos(a), 0, sin(a)], [0, 1, 0], [-sin(a), 0, cos(a)]];
function rz(a) = [[cos(a), -sin(a), 0], [sin(a), cos(a), 0], [0, 0, 1]];
function m4(R, P) = [[R[0][0], R[0][1], R[0][2], P[0]],
                     [R[1][0], R[1][1], R[1][2], P[1]],
                     [R[2][0], R[2][1], R[2][2], P[2]],
                     [0, 0, 0, 1]];

// ---------- Кисть ----------
// Палец: [имя, основание (сустав MCP), начальный поворот, длины фаланг,
//         радиус, сгибы суставов (°), фаланга с датчиком, радиус седла держателя,
//         длина ногтевой фаланги для держателя (finger_dl / pinky_dl / thumb_dl)]
// Все пять держателей — на НОГТЕВЫХ фалангах, задний торец в 1 мм от сустава DIP
// (у большого — от межфалангового сустава). Ногтевая фаланга модели — капсула длиной L
// от сустава плюс скруглённый кончик 0,85·R: от сустава до кончика ≈ L + 0,85·R.
// Поворот пальцев: разведены (spread = 1) … сведены (spread = 0).
function spr_a(a1, a0) = rz(a0 + spread*(a1 - a0));
fingers = [
    ["index",  [-30, 86, -1], spr_a(22, -4),  [44, 25, 16.0], 9.6, [10, 22, 10], 3, 8.0, 22],
    ["middle", [ -8, 90, -1], spr_a(4, 0),    [47, 28, 17.5], 9.7, [12, 24, 10], 3, 8.0, 22],
    ["ring",   [ 14, 87, -1], spr_a(-14, 4),  [44, 26, 16.5], 9.4, [14, 26, 12], 3, 8.0, 22],
    ["pinky",  [ 36, 78, -2], spr_a(-36, 9),  [37, 20, 12.0], 8.5, [16, 28, 12], 3, 7.0, 18],
    // большой: пястная кость, основная и ногтевая фаланги; датчик на ногтевой
    ["thumb",  [-28, 24, -8], rz(42)*rx(-12)*ry(-55), [44, 32, 17.5], 11.4, [8, 14, 12], 3, 9.0, 25]
];

function seg_r(f, i) = f[4]*(1 - 0.06*i);                  // радиус фаланги i (1..3)
function fR(f, i) = i == 0 ? f[2] : fR(f, i - 1)*rx(-f[5][i - 1]);
function fP(f, i) = i == 0 ? f[1] : fP(f, i - 1) + fR(f, i)*[0, f[3][i - 1], 0];
// кадр держателя; держатель опущен, если палец тоньше седла (седло-призма)
function mR(f) = fR(f, f[6]);
function m_drop(f) = max(0, (f[7] + 0.3) - seg_r(f, f[6]))*sqrt(2);
// центр платы вдоль ногтевой фаланги: задний торец в dip_gap от сустава DIP
function m_along(f) = mount_back() + mount_dip_gap();
function mC(f) = fP(f, f[6] - 1) + mR(f)*[0, m_along(f), 0];   // точка на оси пальца
function mP(f) = mC(f) + mR(f)*[0, 0, -m_drop(f)];
function mW(f, p) = mP(f) + mR(f)*p;

// Кольцо-фиксатор (лента 6 мм) + печатная клипса сверху, в которую защёлкивается кабель Ø3
module cable_clip(rho) {
    color(c_ring) rotate([90, 0, 0]) difference() {
        cylinder(r = rho + 1.3, h = 6, center = true);
        cylinder(r = rho, h = 7, center = true);
    }
    color(c_print) translate([0, 0, rho + 1.2]) difference() {
        union() {
            translate([0, 0, 0]) rbox([7, 6, 1.4], 1.2);
            translate([0, 3, 3.3]) rotate([90, 0, 0]) cylinder(d = 5.2, h = 6, $fn = 24);
        }
        translate([0, 4, 3.3]) rotate([90, 0, 0]) cylinder(d = 3.1, h = 8, $fn = 24);
        translate([-1.1, -4, 4.4]) cube([2.2, 8, 5]);
    }
}

module capsule(l, r1, r2) { hull() { sphere(r1); translate([0, l, 0]) sphere(r2); } }

module finger(f) {
    color(c_skin) for (i = [1:3]) multmatrix(m4(fR(f, i), fP(f, i - 1)))
        capsule(f[3][i - 1], seg_r(f, i), i == 3 ? seg_r(f, i)*0.85 : seg_r(f, i));
}

palm_ell = [
    [[  1, 84, -1], [42,  8, 11.5]],  // линия костяшек
    [[-24, 32, -5], [14, 22, 13]],    // возвышение большого пальца
    [[ 27, 45, -3], [10, 28, 12]]     // возвышение мизинца
];
module ell_disk(y, ax, az, cz) { translate([0, y, cz]) rotate([-90, 0, 0]) scale([ax, az, 1]) cylinder(r = 1, h = 0.1, $fn = 48); }
module palm(g = 0) {
    hull() {
        ell_disk(-2, 30 + g, 15 + g, 0);   // запястье
        translate([0, 10, 0]) scale([31 + g, 8, 15 + g]) sphere(1, $fn = 40);
        for (e = palm_ell) translate(e[0]) scale(e[1] + [g, g, g]) sphere(1, $fn = 40);
    }
}
module forearm(g = 0) {
    hull() {
        ell_disk(  4, 30 + g, 16 + g, 0);
        ell_disk(-230, 40 + g, 30 + g, -5);
    }
}
function arm_ax(y) = 30 + 10*(4 - y)/234;
function arm_az(y) = 16 + 14*(4 - y)/234;
function arm_cz(y) = -5*(4 - y)/234;
function arm_top(y) = arm_cz(y) + arm_az(y);

module hand() {
    color(c_skin) { palm(); forearm(); }
    for (f = fingers) finger(f);
}

// ---------- Перчатка без пальцев ----------
module slab(y0, y1) { translate([-100, y0, -100]) cube([200, y1 - y0, 200]); }

module glove() {
    color(c_glove) {
        palm(1.3);
        intersection() { forearm(1.3); slab(-18, 8); }
        // короткие «обрубки» пальцев перчатки: держатели стоят на голом пальце
        for (f = fingers) {
            n = f[0] == "thumb" ? 2 : 1;
            for (i = [1:n]) multmatrix(m4(fR(f, i), fP(f, i - 1)))
                capsule(f[3][i - 1]*(i == n ? (f[0] == "thumb" ? 0.45 : 0.12) : 1), seg_r(f, i) + 1.3, seg_r(f, i) + 1.3);
        }
    }
    color(c_cuff) intersection() { forearm(3.0); slab(-15, 3); }
    color(c_cuff) translate([31, -15, -6]) cube([4, 18, 14]);   // язычок застёжки
}

// ---------- Под на тыле кисти ----------
pod_pos  = [3, 44, 17.0];   // центр низа пода (над липучкой 3 мм)
pod_tilt = -3.3;            // наклон по скату тыла кисти
function podW(p) = pod_pos + rx(pod_tilt)*p;

module pod_on_hand() {
    translate(pod_pos) rotate([pod_tilt, 0, 0]) {
        pod_base();
        pod_electronics(false);
        pod_deck();
        pod_lid();
        color(c_velcro) translate([0, 0, -3]) rbox([30, 30, 3], 2);
    }
}

// ---------- Держатели на пальцах ----------
module mount_unit(r, dl, cut = false, wires = true, n = 0) {
    mount_base(r, dl);
    mount_board(r, wires, 2);
    mount_hardware(r, true);
    if (cut) intersection() { mount_cover(r, n); translate([0, -60, -1]) cube([100, 120, 100]); }
    else mount_cover(r, n);
}
function f_num(f) = f[0] == "thumb" ? 1 : f[0] == "index" ? 2 : f[0] == "middle" ? 3 : f[0] == "ring" ? 4 : 5;

// Кольца-фиксаторы с клипсами: [сегмент, доля длины]. Пальцы — на средней и основной
// фалангах (между петлями над DIP, PIP и MCP), большой — на основной фаланге.
function clip_at(f) = f[0] == "thumb" ? [[2, 0.70]] : [[2, 0.50], [1, 0.62]];
function clip_P(f, c) = fP(f, c[0] - 1) + fR(f, c[0])*[0, f[3][c[0] - 1]*c[1], 0];

// крепление на палец: кольцо ленты 10 мм (у сустава DIP) или напалок из TPU
module tip_fix(r) { if (mount_tip_style() == "thimble") finger_thimble(r); else strap_ring(r); }

module mounts() {
    for (f = fingers) {
        multmatrix(m4(mR(f), mP(f))) {
            mount_unit(f[7], f[8], false, false, f_num(f));
            tip_fix(f[7]);
        }
        for (c = clip_at(f)) multmatrix(m4(fR(f, c[0]), clip_P(f, c))) cable_clip(seg_r(f, c[0]));
    }
}

// ---------- Кабели ----------
function cr(p0, p1, p2, p3, t) =
    0.5*((2*p1) + (-p0 + p2)*t + (2*p0 - 5*p1 + 4*p2 - p3)*t*t + (-p0 + 3*p1 - 3*p2 + p3)*t*t*t);
function spline(pts, n = 8) = let(N = len(pts), P = concat([pts[0]], pts, [pts[N - 1]]))
    [for (i = [0:N - 2]) for (k = [0:n - 1]) cr(P[i], P[i + 1], P[i + 2], P[i + 3], k/n), pts[N - 1]];

module tube(pts, d) {
    for (i = [0:len(pts) - 2]) hull() {
        translate(pts[i]) sphere(d = d, $fn = 10);
        translate(pts[i + 1]) sphere(d = d, $fn = 10);
    }
}

function slot_of(name) =
    name == "index"  ? pod_slots()[0] :
    name == "middle" ? pod_slots()[1] :
    name == "ring"   ? pod_slots()[2] :
    name == "pinky"  ? pod_slots()[3] : pod_slots()[4];

// кабель по тыльной стороне пальца: через клипсу (3 точки вдоль оси клипсы)
function clip_run(f, c) = let(h = seg_r(f, c[0]) + 4.5)
    [for (d = [3, 0, -3]) clip_P(f, c) + fR(f, c[0])*[0, d, h]];
// петля-запас над суставом между сегментами i и i+1
function joint_loop(f, i, h = 7.5) = fP(f, i) + fR(f, i + 1)*[0, -1, seg_r(f, i + 1) + h];

function cable_pts(f) = let(
    s   = f[6],
    r   = f[7],
    rho = seg_r(f, s),
    sl  = slot_of(f[0]),
    zs  = pod_dims()[3] - sl[4] + sl[5]/2,
    out = f[0] == "thumb" ? [sl[0] - 4, sl[1], zs] : [sl[0], sl[1] + 4, zs],
    inn = f[0] == "thumb" ? [sl[0] + 4, sl[1], zs] : [sl[0], sl[1] - 5, zs],
    e   = mount_exit(r),
    yb  = -mount_back(),
    md  = m_drop(f)
) concat(
    // выход из окна в заднем торце (стяжка) → вниз к пальцу
    [mW(f, e + [0, 2, 0]), mW(f, e), mW(f, [e[0]*0.5, yb - 2.5, max(rho + 5 + md, e[2] - 3)])],
    f[0] == "thumb"
      ? concat([joint_loop(f, 2)],                                      // петля над межфаланговым суставом
               clip_run(f, clip_at(f)[0]),                              // клипса на основной фаланге
               [fP(f, 1) + fR(f, 1)*[0, -2, seg_r(f, 2) + 8]])          // петля над MCP большого
      : concat([joint_loop(f, 2)],                                      // петля над DIP
               clip_run(f, clip_at(f)[0]),                              // клипса на средней фаланге
               [joint_loop(f, 1, 8)],                                   // петля над PIP
               clip_run(f, clip_at(f)[1]),                              // клипса на основной фаланге
               [fP(f, 0) + fR(f, 1)*[0, -2, seg_r(f, 1) + 8.5],          // петля над костяшкой
                [(f[1][0] + podW(out)[0])/2, (f[1][1] + podW(out)[1])/2 + 3, podW(out)[2] + 2]]),
    [podW(out), podW(inn)]
);

wb_y    = -45 - wb_dims()[1]/2;            // торец коробки у кисти — в 45 мм от складки запястья
wb_pos  = [0, wb_y, arm_top(wb_y) + 2.0];
wb_tilt = -2.3;
function wbW(p) = wb_pos + rx(wb_tilt)*p;

module cables() {
    color(c_cable) for (f = fingers) tube(spline(cable_pts(f)), 3.0);
    e = wb_pwr_exit();
    sl = pod_slots()[5];
    zs = pod_dims()[3] - sl[4] + sl[5]/2;
    color(c_power) tube(spline([
        wbW(e + [0, -4, 0]), wbW(e + [0, 4, 0]),
        [e[0] - 2, -32, arm_top(-32) + 4],
        [-6, -6, 30],                         // петля-запас над сгибом запястья
        [sl[0] + 3, 6, 40],
        podW([sl[0], sl[1] - 4, zs]), podW([sl[0], sl[1] + 5, zs])
    ]), 2.6);
}

// ---------- Браслет ----------
module wrist_unit() {
    translate(wb_pos) rotate([wb_tilt, 0, 0]) {
        wrist_box_base();
        wrist_box_electronics();
        wrist_box_lid();
        color([0.05, 0.05, 0.05]) translate([0, 0, -2]) rbox([36, 52, 2], 3);   // прокладка EVA
    }
    y = wb_pos[1];
    lx = wb_lug_x();
    color(c_strap) translate([0, y, 0]) rotate([90, 0, 0]) linear_extrude(25, center = true)
        difference() {
            offset(r = 1.8) strap_shape(y, lx);
            strap_shape(y, lx);
        }
}
module strap_shape(y, lx) {
    hull() {
        translate([0, arm_cz(y)]) scale([arm_ax(y) + 0.3, arm_az(y) + 0.3]) circle(1, $fn = 60);
        for (sx = [-1, 1]) translate([sx*lx - 0.6, wb_pos[2] + 2]) square([1.2, 1], center = true);
    }
}

// ---------- Разнесённый вид пода ----------
module pod_exploded() {
    h = pod_dims()[2];
    pod_base();
    translate([0, 0, 0.9*h]) pod_electronics(true);
    if (pod_has_deck()) translate([0, 0, 0.9*h]) pod_deck();
    translate([0, 0, 1.9*h + 12]) pod_lid();
    color(c_velcro) translate([0, 0, -14]) rbox([30, 30, 3], 2);
}

// ---------- Разнесённая коробка питания ----------
module wrist_exploded() {
    wrist_box_base();
    wrist_box_electronics();
    translate([0, 0.45*wb_dims()[1], wb_dims()[2] + 10]) wrist_box_lid();   // крышка поднята и сдвинута к кисти
}

// ---------- Держатель на кончике пальца крупно ----------
// Ногтевая фаланга R 8 / 22 мм, сустав DIP в 1 мм за держателем, средняя фаланга R 8,6
// с кольцом-клипсой; кабель — петлёй над DIP.
module fingertip(r, dl, yd, mid = 30) {
    color(c_skin) {
        translate([0, yd, 0]) rotate([-90, 0, 0]) hull() {      // ногтевая фаланга
            sphere(r + 0.4, $fn = 64);
            translate([0, 0, dl - 0.9*r]) sphere(0.9*r, $fn = 64);
        }
        translate([0, yd - mid, 0]) rotate([-90, 0, 0]) cylinder(r = r + 0.6, h = mid, $fn = 64);   // средняя
        translate([0, yd - mid, 0]) scale([1.05, 0.8, 1.0]) sphere(r + 1.0, $fn = 48);         // сустав PIP
        translate([0, yd, 0]) scale([1.05, 0.8, 1.0]) sphere(r + 0.7, $fn = 48);              // сустав DIP
    }
}
module closeup() {
    r = 8.0; dl = 22;
    yd = -mount_back() - mount_dip_gap();                       // складка DIP
    fingertip(r, dl, yd, 34);
    mount_unit(r, dl, true, true, 2);
    tip_fix(r);
    e = mount_exit(r);
    yc = yd - 16;                                                // кольцо с клипсой на средней фаланге
    zc = r + 0.6 + 4.5;                                          // ось кабеля в клипсе
    color(c_cable) tube(spline([e + [0, 1.5, 0], e, [e[0]*0.5, e[1] - 2.5, max(zc + 1, e[2] - 3)],
                                [0, yd - 1, r + 9], [0, yc + 3, zc], [0, yc, zc], [0, yc - 3, zc], [0, yd - 34, zc + 1]]), 3.0);
    translate([0, yc, 0]) cable_clip(r + 0.6);
}

// ---------- Раскладка на столе принтера ----------
module label(t, p, s = 4.0) {
    color([0.15, 0.15, 0.15]) translate(p) linear_extrude(0.4)
        text(t, size = s, font = "Liberation Sans", halign = "center", valign = "center");
}
module layout() {
    color([0.80, 0.80, 0.82]) translate([-140, -95, -1.01]) cube([280, 190, 1]);
    translate([-100, 45, 0]) pod_base();             label("pod_base.stl", [-100, 9, 0]);
    translate([-38, 45, 0]) pod_lid_print();          label("pod_lid.stl", [-38, 9, 0]);
    translate([28, 45, 0]) wrist_box_base();         label("wrist_box.stl", [28, 9, 0]);
    translate([85, 45, 0]) wrist_box_lid_print();    label("wrist_box_lid.stl", [85, 9, 0]);
    for (i = [0:2]) translate([-120 + i*31, -20, -0.4*8.0]) color(c_mount) render() mount_base(8.0);
    label("finger_mount.stl x3", [-89, -40], 3.5);
    translate([-24, -20, -0.4*7.0]) color(c_mount) render() mount_base(7.0, 18);
    label("..._pinky.stl", [-24, -40], 3.5);
    translate([10, -20, -0.4*9.0]) color(c_mount) render() mount_base(9.0, 25);
    label("..._thumb.stl", [12, -40], 3.5);
    for (i = [0:4]) translate([-120 + i*31, -68, -mount_board_z(8.0) - 2.3]) color(c_cover) render() mount_cover(8.0);
    label("finger_cover.stl x5", [-58, -90], 3.5);
    for (i = [0:4]) translate([45 + i*15, -20, 0.8]) rotate([180, 0, 0]) translate([0, 0, 0]) dupont_sleeve();
    label("dupont_sleeve.stl x6", [75, -32], 3.5);
    translate([75, -66, 0]) fit_gauge();
    label("fit_gauge.stl", [75, -88], 3.5);
    translate([120, -20, 0.8]) rotate([180, 0, 0]) dupont_sleeve();
}

// ---------- Проверка столкновений держателей ----------
// Выпуклая оболочка держателя (основание + крышка), раздутая на g со всех сторон
module mount_hull(f, g) {
    multmatrix(m4(mR(f), mP(f))) minkowski() {
        hull() { mount_base(f[7], f[8]); mount_cover(f[7], 0); }
        cube(max(g, 0.01), center = true);
    }
}
module collide() { intersection() { mount_hull(fingers[ci], gap); mount_hull(fingers[cj], 0.01); } }

// =====================================================================
if (explode) pod_exploded();
else if (view == "layout") layout();
else if (view == "collide") collide();
else if (view == "closeup") closeup();
else if (view == "wrist_exploded") wrist_exploded();
else {
    hand();
    glove();
    pod_on_hand();
    mounts();
    cables();
    wrist_unit();
}
