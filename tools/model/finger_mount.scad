// =====================================================================
// AirGlove — держатель датчика GY-BNO055 на КОНЧИК пальца (ногтевая фаланга,
// со стороны ногтя). Перчатка без пальцев, кончики голые: подушечка остаётся
// открытой — можно касаться и печатать.
//
// Три способа подключения (переключатель conn_mode в common.scad, можно задать
// отдельно для держателя: fm_mode):
//   dupont_straight — заводская гребёнка, 4-контактный Dupont надет вертикально,
//                     над разъёмом колпак (самый высокий, ~31–33 мм над пальцем);
//   dupont_bent     — штыри загнуты К КОНЧИКУ, корпус Dupont лежит плашмя НАД ПЛАТОЙ,
//                     провода петлёй возвращаются над корпусом к кисти (~16–18 мм);
//   soldered_stubs  — планка снята, провода припаяны к пенькам (~10–12 мм).
// Во всех режимах одинаковы: длина 26,7 × ширина 27,2 мм, карман +0,8 мм на сторону
// с 6 пружинящими язычками, винты M2 в плавающих гайках (паз ±1,2 мм), прижимная
// крышка, тестовая рамка.
//
// Крепление на палец — tip_style:
//   "strap"   — кольцо из ленты-липучки 10 мм через канал под платой (у сустава DIP);
//   "thimble" — защёлкивающийся напалок из TPU: С-образная скоба охватывает бока
//               фаланги и цепляется за пазы на «щеках» основания; снизу открыта —
//               подушечка свободна. Основание без канала ленты на 1,8 мм ниже.
//
// Система координат: палец вдоль Y (+Y — к кончику), ось пальца через (0,0,0),
// Z вверх (тыльная сторона, ноготь). Центр платы — над осью пальца (x = 0, y = 0).
// Ряд контактов платы — со стороны кисти (-Y), ось X датчика смотрит к кончику пальца.
// Задний торец держателя (y = -13,35) стоит в dip_gap = 1 мм от складки сустава DIP,
// поэтому держатель НЕ заходит на сустав, а свешивается вперёд за кончик пальца.
//
// Детали:
//   base    — основание: седло на ногтевую фалангу, канал ленты 10 мм (strap) или пазы
//             под напалок (thimble), карман под плату, выемки под хвосты и кварц,
//             2 канала под гайки M2, снизу спереди подрезано над кончиком пальца;
//   cover   — крышка с номером пальца num = 1…5 (1 — большой … 5 — мизинец);
//   thimble — напалок из TPU (для tip_style = "thimble");
//   sleeve  — насадка на 4-контактный корпус Dupont (только dupont_straight);
//   jig     — шаблон: для bent — гибка штырей на 0,6 мм над планкой, для stubs —
//             обрезка пеньков ровно 1,5 мм;
//   gauge   — тестовая рамка 1,2 мм для проверки посадки платы (печать ~10 мин).
// Метизы: A, C — 2 винта M2×10 + 2 гайки M2; B — 1 винт M2×10 (через крышку)
// + 1 винт M2×6 (головкой прямо на плату, под петлёй проводов) + 2 гайки M2.
//
// Экспорт (из папки tools/model), режим задаётся -D 'conn_mode="..."':
//   openscad -o finger_mount.stl         -D 'part="base"'  finger_mount.scad
//   openscad -o finger_mount_pinky.stl   -D 'part="base"'  -D 'variant="pinky"' finger_mount.scad
//   openscad -o finger_mount_thimble.stl -D 'part="base"'  -D 'tip_style="thimble"' finger_mount.scad
//   openscad -o finger_thimble.stl       -D 'part="thimble"' finger_mount.scad
//   openscad -o finger_cover_2.stl       -D 'part="cover"' -D 'num=2' finger_mount.scad
//   openscad -o dupont_sleeve.stl        -D 'part="sleeve"' finger_mount.scad
//   openscad -o pin_jig.stl              -D 'part="jig"'   finger_mount.scad
//   openscad -o fit_gauge.stl            -D 'part="gauge"' finger_mount.scad
// Все детали печатаются без поддержек, в STL уже повёрнуты как печатать.
// =====================================================================

include <common.scad>

part      = "demo";     // "base" | "cover" | "thimble" | "sleeve" | "jig" | "gauge" | "demo"
variant   = "finger";   // "finger" (указательный/средний/безымянный) | "pinky" | "thumb"
tip_style = "strap";    // "strap" — лента-липучка | "thimble" — напалок из TPU
num       = 0;          // номер пальца на крышке: 1 — большой, 2 — указательный … 5 — мизинец; 0 — без номера
fm_mode   = conn_mode;  // способ подключения для держателя
$fn = 48;

// ---------- Палец: НОГТЕВАЯ фаланга ----------
// Радиус = обхват ногтевой фаланги посередине / 6,28. Длина — от складки сустава DIP
// (на тыльной стороне) до самого кончика пальца.
finger_r  = 8.0;   // указательный, средний, безымянный (обхват ~50 мм). ИЗМЕРЬТЕ
pinky_r   = 7.0;   // мизинец (обхват ~44 мм). ИЗМЕРЬТЕ
thumb_r   = 9.0;   // большой (обхват ~57 мм). ИЗМЕРЬТЕ
finger_dl = 22;    // длина ногтевой фаланги, указательный/средний/безымянный (20–25). ИЗМЕРЬТЕ
pinky_dl  = 18;    // мизинец. ИЗМЕРЬТЕ
thumb_dl  = 25;    // большой. ИЗМЕРЬТЕ
dip_gap   = 1.0;   // от складки DIP до заднего торца держателя: сустав сгибается свободно
fit       = 0.3;   // зазор седло–палец
flat_dz   = 0.3;   // плоская «полочка» на верху седла-капли (мост при печати)
wing_k    = 0.4;   // низ «щёк» седла = wing_k × радиус

// ---------- Лента-кольцо (tip_style = "strap") ----------
strap_w    = 10;   // ширина ленты-липучки (10 мм; 12 мм — поставьте 12, подушечка закроется сильнее)
strap_t    = 1.8;  // толщина ленты (крючки+петли одним куском ~1,5–2 мм)
strap_back = 1.2;  // от заднего торца держателя до канала ленты

// ---------- Напалок из TPU (tip_style = "thimble") ----------
// С-образная скоба: охватывает бока фаланги, проходит под нижними гранями «щёк» основания
// и защёлкивается зубьями в два паза в этих гранях. Снизу вырез — подушечка открыта.
th_t       = 1.6;  // толщина стенки напалка
th_squeeze = 0.3;  // натяг: внутренний радиус на 0,3 мм меньше седла — держит палец
th_gap     = 50;   // полуугол выреза снизу (от оси подушечки): подушечка открыта на ~2·R·sin50°
th_len     = 10;   // длина напалка вдоль пальца
th_nw      = 1.0;  // паз в нижней грани щеки: ширина
th_nd      = 1.0;  // паз: глубина (зуб напалка 0,8 × 0,9)

// ---------- ДОПУСКИ: плата любого размера из диапазона садится без подгонки ----------
pcb_clear  = 0.8;   // зазор кармана на сторону от номинала (плата 21,0 входит от 19,4 до 22,6)
pcb_t_min  = 1.2;   // самая тонкая плата, которую ещё прижмёт крышка
pcb_t_max  = 2.0;   // самая толстая плата, на которую ещё садится крышка
tail_extra = 1.0;   // выемка под хвосты = хвост + 1 мм (хвост 3,0; в режиме stubs 1,0)
floor_min  = 0.8;   // минимальное дно под выемкой хвостов
xtal_rec   = 0.8;   // глубина выемки под кварц/выводы вдоль края с отверстиями
comp_clear = 3.6;   // высота под крышкой над платой (кварц до 3 мм + запас)

// Пружинящие язычки (вертикальные, корень глубоко в основании, «зуб» на конце
// упирается в торец платы). u — от стенки кармана наружу.
spr_pre  = 0.2;   // натяг: зуб выступает внутрь номинального контура платы на 0,2
spr_bump = 0.5;   // высота зуба
spr_t    = 0.8;   // толщина язычка
spr_room = 1.2;   // ход язычка наружу (плата больше номинала на 2×(1,2-0,2)=2 мм — ещё влезет)
spr_skin = 0.8;   // наружная стенка за язычком
spr_w    = 3.0;   // ширина язычка
spr_len  = 6.0;   // длина язычка (корень на spr_len ниже дна кармана; укорачивается, если под ним седло)
spr_len_front = 5.5;  // у переднего края язычки короче (там гайки)
spr_side_y  = [-4, 2];       // язычки на длинных сторонах (по Y)
spr_hand_x  = [-8.8, 8.8];   // на стороне кисти (по X) — вынесены к углам, над «щеками» седла
spr_front_x = [-8.8, 8.8];   // на стороне кончика (по X)

// ---------- Винты и гайки M2 ----------
m2_d     = 2.4;   // отверстие под винт M2 (в крышке и основании)
hole_fx  = 1.2;   // паз: допуск положения отверстий платы по X ±1,2 мм
nut_af   = 4.0;   // гайка M2 под ключ
nut_h    = 1.6;   // высота гайки
nut_skin = 0.8;   // пластик между выемкой кварца и гайкой
head_well = 4.4;  // колодец под головку винта, если крыша выше посадки головки

// ---------- Крышка ----------
cov_t    = 1.2;   // толщина стенок и крыши
cov_r    = 3.0;   // скругление углов в плане
cov_f    = 2.5;   // скругление верхних кромок
foam_pcb = 1.0;   // вспененный скотч на прижимных полках (сжимается до ~0,3)
foam_dup = 2.0;   // straight: полоска EVA 2 мм на перемычке колпака
foam_loop = 2.0;  // bent: полоска EVA 2 мм на лежачем корпусе, под петлёй проводов
loop_r   = 2.0;   // bent: радиус петли проводов на выходе из корпуса (силикон 28 AWG)
ledge_in = 9.0;   // прижимные полки заходят на плату до |x| = 9,0
pin_d    = 1.5;   // штифты-фиксаторы крышки

// ---------- Насадка на корпус Dupont (dupont_straight) ----------
slv_cl   = 0.15;  // зазор насадки на корпус
slv_wall = 0.9;
slv_h    = 5.0;   // насколько насадка опускается по корпусу
slv_top  = 0.8;   // толщина верхней губки
slv_lip  = 0.7;   // губка начинается в 0,7 мм от оси провода (провод Ø1,1 свободен)

// =====================================================================
// Производные размеры
// =====================================================================
M  = fm_mode;
TS = tip_style;
function r_of(v)  = v == "pinky" ? pinky_r  : v == "thumb" ? thumb_r  : finger_r;
function dl_of(v) = v == "pinky" ? pinky_dl : v == "thumb" ? thumb_dl : finger_dl;
R  = r_of(variant);
DL = dl_of(variant);

px = bno_a/2 + pcb_clear;              // полуширина кармана (11,3)
py = bno_b/2 + pcb_clear;              // полудлина кармана (11,05)
wall_t = -(pcb_clear + spr_pre) + spr_bump + spr_t + spr_room + spr_skin;  // 2,3
ox = px + wall_t;                       // полуширина держателя (13,6)
oy = py + wall_t;                       // полудлина держателя (13,35)
tail_rec = tail_h(M) + tail_extra;      // 4,0 (stubs: 2,0)

yr  = bno_row_y();                      // ось ряда контактов (-8,95)
hx  = bno_hous_x();                     // центр разъёма по X (-5,08)
yhw0 = yr + 3.0;                        // straight: задняя граница колпака над разъёмом
yhw1 = yhw0 + cov_t;
ycb0 = yr + 1.25;                       // straight: перемычка от провода с запасом 0,7 по Y
holes = bno_holes();
y_back = -oy;                           // задний (к кисти) торец — одинаков во всех режимах
win_w  = 10.4;                          // окно выхода проводов в заднем торце
ys0 = y_back + strap_back;              // канал ленты / зона напалка: от ys0 ...
ys1 = ys0 + strap_w;                    // ... до ys1 (у сустава DIP — подушечка открыта)
y_dip = y_back - dip_gap;               // складка сустава DIP
function y_tip(dl) = y_dip + dl;        // кончик пальца
yhe = yr + bent_gap + dup_l;            // bent: торец лежачего корпуса (к кончику), 5,85
// bent: винт со стороны разъёма ставится прямо на плату (над ним идёт петля проводов),
// крышку держит второй винт
function cov_holes() = m_bent(M) ? [for (h = holes) if (sign(h[0]) != sign(hx)) h] : holes;
function low_holes() = m_bent(M) ? [for (h = holes) if (sign(h[0]) == sign(hx)) h] : [];

function strap_h()  = TS == "strap" ? strap_t : 0;
function zp_of(r)   = r + fit + flat_dz + strap_h() + floor_min + tail_rec;   // низ платы над осью пальца
function zst_of(r)  = zp_of(r) + pcb_t_max + 0.3;                  // верх стенок основания = посадка крышки
function zlow_of(r) = zp_of(r) + bno_pcb + comp_clear;             // низ крыши над платой (кварц)
function zht_of(r)  = zp_of(r) + bno_pcb + dup_top;                // straight: верх корпуса Dupont
function zhax_of(r) = zp_of(r) + bno_pcb + bent_z;                 // bent: ось лежачего корпуса
function zloop_of(r) = zhax_of(r) + 2*loop_r;                      // bent: обратная ветка петли проводов
function zwire_of(r) = m_str(M) ? zht_of(r) + dup_bend_r - 0.3
                     : m_bent(M) ? zloop_of(r) : zp_of(r) + bno_pcb + stub_len*0.55;
function zceil_of(r) = m_str(M)  ? zht_of(r) + dup_bend_h + 0.5     // низ потолка колпака
                     : m_bent(M) ? max(zlow_of(r), zloop_of(r) + wire_d/2)
                     :             zlow_of(r);
function ztop_of(r) = zceil_of(r) + cov_t;                          // верх держателя
function zcb_of(r)  = zht_of(r) + slv_top + 1.4;                    // straight: низ перемычки
function zseat_of(r) = zlow_of(r) + cov_t;                          // посадка головки винта (M2×10)
function zcut_of(r) = zp_of(r) - spr_len - 0.8;                     // низ основания над кончиком пальца
// «Щёки» седла: низ на wing_k·r, полуширина r + 2,6; если основание низкое (C, напалок),
// щёки расширяются, чтобы колодцы язычков (глубина 6 мм) не вышли наружу снизу.
function wz0_of(r) = wing_k*r;
function whx_of(r) = max(r + 2.6, ox - max(0, zcut_of(r) - wz0_of(r) - 0.5));
function zc_of(r)  = max(wz0_of(r) + 0.5, zcut_of(r) - (ox - whx_of(r)));
function xn_of(r)  = (sqrt(pow(r + fit, 2) - pow(wz0_of(r), 2)) + whx_of(r))/2;   // паз под зуб напалка
module base_profile(r) {
    whx = whx_of(r); wz0 = wz0_of(r); zc = zc_of(r); zst = zst_of(r);
    polygon([[-whx, wz0], [whx, wz0], [whx, zc], [ox, zc + max(0, ox - whx)],
             [ox, zst], [-ox, zst], [-ox, zc + max(0, ox - whx)], [-whx, zc]]);
}

// Верх полости под основанием на расстоянии |x| от оси: седло (радиус R1) или канал ленты (Rs).
// Капля: окружность + две касательные под 45° + полочка flat_dz.
function drop_top(Rr, x) = abs(x) >= Rr ? -99
                         : abs(x) > Rr/sqrt(2) ? sqrt(Rr*Rr - x*x)
                         : min(Rr + flat_dz, Rr*sqrt(2) - abs(x));

module teardrop2d(Rr, top) {
    intersection() {
        union() { circle(Rr); rotate(45) square([Rr, Rr]); }
        translate([-2*Rr, -2*Rr]) square([4*Rr, 2*Rr + top]);
    }
}

// ---------- Пружинящий язычок ----------
// Локальная система: u — наружу от стенки кармана (u=0 — грань кармана), v — вдоль стенки.
module spring_cut(zp, zst, len) {
    ub = -(pcb_clear + spr_pre);
    translate([ub - 0.1, -spr_w/2 - 0.5, zp - len]) cube([spr_t + spr_bump + spr_room + 0.2, spr_w + 1.0, zst - zp + len + 1]);
}
module spring_tab(zp, len) {
    ub = -(pcb_clear + spr_pre);
    u0 = ub + spr_bump;
    translate([u0, -spr_w/2, zp - len - 0.05]) cube([spr_t, spr_w, len + 1.05]);
    translate([0, spr_w/2, 0]) rotate([90, 0, 0]) linear_extrude(spr_w)
        polygon([[u0 + 0.01, zp + 0.05], [ub, zp + 0.05], [ub, zp + 0.45], [u0 + 0.01, zp + 1.0]]);
}
// Размещение: side = "L"/"R" (длинные стороны ∓X), "H" (кисть, -Y), "F" (кончик, +Y)
module at_wall(side, s) {
    if (side == "R") translate([px, s, 0]) children();
    if (side == "L") translate([-px, s, 0]) mirror([1, 0, 0]) children();
    if (side == "H") translate([s, -py, 0]) rotate([0, 0, -90]) children();
    if (side == "F") translate([s, py, 0]) rotate([0, 0, 90]) children();
}
// Длина язычка: не больше номинала и с дном 0,6 мм над седлом/каналом ленты под ним
function spr_fit(r, side, s, len) = let(
    zp = zp_of(r),
    vw = spr_w/2 + 0.5,
    xa = side == "H" || side == "F" ? max(0, abs(s) - vw) : px - (pcb_clear + spr_pre) - 0.1,
    yy = side == "H" ? [-py - 2, -py + 1.2] : side == "F" ? [py - 1.2, py + 2] : [s - vw, s + vw],
    in_strap = TS == "strap" && yy[1] > ys0 && yy[0] < ys1,
    zf = max(drop_top(r + fit, xa), in_strap ? drop_top(r + fit + strap_t, xa) : -99)
) min(len, zp - zf - 0.6);
function spring_list(r = finger_r) = concat(
    [for (y = spr_side_y) ["R", y, spr_fit(r, "R", y, spr_len)]], [for (y = spr_side_y) ["L", y, spr_fit(r, "L", y, spr_len)]],
    [for (x = spr_hand_x) ["H", x, spr_fit(r, "H", x, spr_len)]], [for (x = spr_front_x) ["F", x, spr_fit(r, "F", x, spr_len_front)]]);

// =====================================================================
// ОСНОВАНИЕ
// =====================================================================
module mount_base(r = finger_r, dl = finger_dl) {
    zp  = zp_of(r);
    zst = zst_of(r);
    R1  = r + fit;
    Rs  = r + fit + strap_t;
    wz0 = wz0_of(r);                     // низ щёк (стол при печати)
    L   = oy - y_back;
    zcut = zcut_of(r);
    yA  = y_tip(dl) - 1 - max(0, zcut - wz0);   // откуда начинается подрезка над кончиком (45°)
    color(c_print) difference() {
        union() {
            intersection() {
                translate([0, oy, 0]) rotate([90, 0, 0]) linear_extrude(L) base_profile(r);
                // скруглённые вертикальные углы
                translate([0, (oy + y_back)/2, 0]) rbox([2*ox, L, 50], cov_r);
            }
            // штифты-фиксаторы крышки
            for (sx = [-1, 1]) translate([sx*12.5, -oy + 1.0, zst - 0.01]) cylinder(d = pin_d, h = 2.0, $fn = 16);
        }
        // седло под ногтевую фалангу
        rotate([90, 0, 0]) linear_extrude(200, center = true) teardrop2d(R1, R1 + flat_dz);
        // канал ленты — у сустава DIP, подушечка у кончика остаётся открытой
        if (TS == "strap")
            translate([0, ys1, 0]) rotate([90, 0, 0]) linear_extrude(strap_w) teardrop2d(Rs, Rs + flat_dz);
        // пазы под зубья напалка в нижних гранях щёк
        if (TS == "thimble") for (s = [-1, 1])
            translate([s*xn_of(r) - th_nw/2, ys0, wz0 - 1]) cube([th_nw, th_len + 0.4, th_nd + 1]);
        // над кончиком пальца низ основания подрезан (45°), чтобы не мешал печатать и касаться
        translate([60, 0, 0]) rotate([0, -90, 0]) linear_extrude(120)
            polygon([[wz0 - 30, yA - 30], [wz0 - 0.01, yA], [zcut, yA + max(0, zcut - wz0)], [zcut, 80], [wz0 - 30, 80]]);
        // карман под плату
        translate([-px, -py, zp]) cube([2*px, 2*py, 20]);
        // передняя стенка (у края с отверстиями и кварцем) опущена до zp + 1,0
        translate([-ox - 1, py - 0.01, zp + pcb_t_min - 0.2]) cube([2*ox + 2, wall_t + 1, 20]);
        // выемка под хвосты штырей: на всю ширину, глубина хвост + 1
        translate([-px + 0.9, -py - 0.01, zp - tail_rec]) cube([2*px - 1.8, -7.3 + py, tail_rec + 0.1]);
        // выемка под кварц и его выводы вдоль всего края с отверстиями
        translate([-px + 0.9, bno_b/2 - 7.5, zp - xtal_rec]) cube([2*px - 1.8, py - (bno_b/2 - 7.5) + 0.01, xtal_rec + 0.1]);
        // винты M2: паз ±1,2 по X, канал гайки открыт наружу (гайка вставляется сбоку)
        for (h = holes) {
            sx = sign(h[0]);
            zn1 = zp - xtal_rec - nut_skin;            // верх гайки
            translate([h[0], h[1], zn1 - 0.01]) slot_x(m2_d, hole_fx, xtal_rec + nut_skin + 0.1);
            translate([sx > 0 ? h[0] - hole_fx - nut_af*0.578 : -ox - 1, h[1] - (nut_af + 0.2)/2, zn1 - nut_h - 0.2])
                cube([ox + 1 - abs(h[0]) + hole_fx + nut_af*0.578, nut_af + 0.2, nut_h + 0.2]);
            translate([h[0], h[1], zn1 - nut_h - 0.2 - 1.0]) slot_x(m2_d, hole_fx, 1.1);   // кончик винта
        }
        // колодцы пружинящих язычков
        for (s = spring_list(r)) at_wall(s[0], s[1]) spring_cut(zp, zst, s[2]);
    }
    color(c_print) for (s = spring_list(r)) at_wall(s[0], s[1]) spring_tab(zp, s[2]);
}

// =====================================================================
// НАПАЛОК из TPU (tip_style = "thimble"): профиль в плоскости XZ рабочего положения
// =====================================================================
module thimble2d(r) {
    R1  = r + fit - th_squeeze;
    wz0 = wz0_of(r);
    xn  = xn_of(r);
    intersection() {
        difference() {
            offset(r = th_t) union() { circle(R1, $fn = 72); base_profile(r); }
            union() { circle(R1, $fn = 72); base_profile(r); }
            polygon([[0, 0], [-60*tan(th_gap), -60], [60*tan(th_gap), -60]]);   // подушечка открыта
        }
        translate([-xn - 1.4, -50]) square([2*xn + 2.8, 50 + wz0]);   // скоба кончается за пазом
    }
    // зубья в пазы щёк
    for (s = [-1, 1]) translate([s*xn - 0.4, wz0 - 0.5]) square([0.8, 0.5 + th_nd - 0.1]);
}
module finger_thimble(r = finger_r) {
    color(c_tpu) translate([0, ys0 + 0.2 + th_len, 0]) rotate([90, 0, 0]) linear_extrude(th_len) thimble2d(r);
}
c_tpu = [0.30, 0.31, 0.33];

// Кольцо из ленты-липучки в канале (только для картинок)
module strap_ring(r = finger_r) {
    color([0.10, 0.10, 0.11]) translate([0, (ys0 + ys1)/2, 0]) rotate([90, 0, 0]) difference() {
        cylinder(r = r + fit + strap_t, h = strap_w - 0.2, center = true, $fn = 64);
        cylinder(r = r + 0.05, h = strap_w + 1, center = true, $fn = 64);
    }
}

// =====================================================================
// КРЫШКА (в рабочем положении; для печати опускается на z_stop = 0)
// =====================================================================
// Оболочка: d = 0 — снаружи, d = cov_t — полость
module cover_env(r, d) {
    zst = zst_of(r);
    z0  = zst - (d > 0 ? 1 : 0);
    rc  = cov_r - d;
    fr  = max(0.4, cov_f - d);
    if (m_str(M)) hull() {
        // колонна над разъёмом (у кисти) и низкая часть над платой — одной гладкой «горкой»
        translate([0, (-oy + yhw1)/2, z0]) soft_box([2*(ox - d), yhw1 + oy - 2*d, ztop_of(r) - d - z0], rc, 0.3, fr, false, false);
        translate([0, 0, z0]) soft_box([2*(ox - d), 2*(oy - d), zlow_of(r) + cov_t - d - z0], rc, 0.3, fr, false, false);
    } else translate([0, (oy + y_back)/2, z0])
        soft_box([2*(ox - d), oy - y_back - 2*d, ztop_of(r) - d - z0], rc, 0.3, fr, false, false);
}

module cover_number(r, n) {
    if (n > 0) {
        p = m_str(M) ? [6.5, (-oy + yhw1)/2] : m_bent(M) ? [1.5, -2] : [0, 2];
        translate([p[0], p[1], ztop_of(r) - 0.01]) linear_extrude(0.6)
            text(str(n), size = 6, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
    }
}

module mount_cover(r = finger_r, n = num) {
    zp  = zp_of(r);
    zst = zst_of(r);
    zlo = zlow_of(r);
    zce = zceil_of(r);
    ztp = ztop_of(r);
    zcb = zcb_of(r);
    zse = zseat_of(r);
    // bent: полки под лежачим корпусом плоские (корпус в 1,8 мм над платой)
    zlc = m_bent(M) ? zhax_of(r) - dup_w/2 - 0.15 : 99;
    color(c_print2) difference() {
        union() {
            difference() { cover_env(r, 0); cover_env(r, cov_t); }
            // прижимные полки по низу бортов (печатаются на столе), сверху скос 45°
            for (sx = [-1, 1]) mirror([sx < 0 ? 1 : 0, 0, 0]) translate([0, 4.0, 0]) rotate([90, 0, 0])
                linear_extrude(9.5) polygon([[ledge_in, zst], [ox - cov_t + 0.01, zst],
                    [ox - cov_t + 0.01, min(zlc, zst + 0.8 + (ox - cov_t - ledge_in))], [ledge_in, min(zlc, zst + 0.8)]]);
            // уголки под штифты
            for (sx = [-1, 1]) translate([sx > 0 ? 11.4 : -ox + 0.5, -oy, zst]) cube([ox - 11.4 - 0.5, 2.0, 3.0]);
            // бобышки винтов: если крыша выше посадки головки — колодец до zse
            intersection() {
                for (h = cov_holes()) translate([h[0], h[1], zlo]) hull() for (s = [-1, 1])
                    translate([s*hole_fx, 0, 0]) cylinder(d = head_well + 2.4, h = ztp - zlo + 1, $fn = 24);
                cover_env(r, 0);
            }
            if (m_str(M))   // перемычка, прижимающая насадку разъёма (мост между бортами)
                translate([-ox + 0.5, ycb0, zcb]) cube([2*ox - 1, yhw0 - ycb0, 1.5]);
        }
        // пазы под винты M2 (±1,2 по X) и колодцы под головки
        for (h = cov_holes()) {
            translate([h[0], h[1], zlo - 1]) slot_x(m2_d, hole_fx, ztp - zlo + 2);
            translate([h[0], h[1], zse]) slot_x(head_well, hole_fx, ztp);
        }
        // отверстия под штифты
        for (sx = [-1, 1]) translate([sx*12.5, -oy + 1.0, zst - 0.01]) cylinder(d = pin_d + 0.35, h = 2.5, $fn = 16);
        // окно выхода проводов в торце со стороны кисти (снизу открыто — крышка опускается на провода)
        translate([hx - win_w/2, -oy - 1, zst - 1])
            cube([win_w, cov_t + 2.2, (m_stub(M) ? zwire_of(r) + 1.2 : zce) - zst + 1]);
        // прорези под стяжку 2,5 мм — прижимает жгут к крышке (разгрузка разъёма)
        for (sx = [-1, 1])
            translate([hx + sx*4.2 - 0.75, -oy + cov_t + 0.3, zce - 1]) cube([1.5, 2.8, ztp - zce + 3]);
    }
    color(c_accent) cover_number(r, n);
}

// Насадка на 4-контактный корпус Dupont. z = 0 — верх корпуса, центр корпуса в (0,0).
// Открыта в сторону кисти (-Y): провода заводятся сбоку, губка лежит на стороне кончика пальца.
module dupont_sleeve() {
    iw = 4*pitch + 2*slv_cl;
    id = dup_w + 2*slv_cl;
    color(c_print) difference() {
        translate([-iw/2 - slv_wall, -id/2 - slv_wall, -slv_h]) cube([iw + 2*slv_wall, id + 2*slv_wall, slv_h + slv_top]);
        translate([-iw/2, -id/2, -slv_h - 1]) cube([iw, id, slv_h + 1]);
        translate([-iw/2 + 0.6, -id/2 - slv_wall - 1, -0.5]) cube([iw - 1.2, id/2 + slv_wall + 1 + slv_lip, slv_top + 1]);
    }
}

// Шаблон для штырей (8 штук в ряд). bent: пластина 0,6 мм надевается на штыри до планки,
// штыри загибаются через её край — изгиб у всех на одной высоте. stubs: пластина 1,5 мм
// кладётся на плату (планка снята), штыри обкусываются заподлицо — пеньки ровно 1,5 мм.
module pin_jig() {
    t = m_stub(M) ? stub_len : 0.6;
    color(c_print) difference() {
        union() {
            translate([0, 0, 0]) rbox([8*pitch + 8, 9, t], 1.5);
            translate([0, 3.5, 0]) rbox([8*pitch + 8, 2, 4], 0.8);     // ручка-ребро
        }
        translate([-(8*pitch + 0.8)/2, -3.5, -1]) cube([8*pitch + 0.8, 1.0 + 3.5 + 0.0, t + 2]);  // прорезь, открыта с края
    }
}

// Тестовая рамка: контур кармана (зазоры как в основании), пазы винтов, окно под хвосты.
module fit_gauge() {
    color(c_print) difference() {
        translate([0, 0, 0]) rbox([2*ox, 2*oy, 1.2], cov_r);
        translate([-px, -py, 0.6]) cube([2*px, 2*py, 1]);
        translate([-px + 0.9, -py, -1]) cube([2*px - 1.8, -7.3 + py, 3]);
        for (h = holes) translate([h[0], h[1], -1]) slot_x(m2_d, hole_fx, 3);
        difference() {
            translate([-bno_a/2 - 0.2, -bno_b/2 - 0.2, 0.3]) cube([bno_a + 0.4, bno_b + 0.4, 1]);
            translate([-bno_a/2 + 0.2, -bno_b/2 + 0.2, 0]) cube([bno_a - 0.4, bno_b - 0.4, 2]);
        }
        translate([0, 3, -1]) linear_extrude(3) polygon([[-1, -5], [1, -5], [1, 1], [3, 1], [0, 5], [-3, 1], [-1, 1]]);
    }
    color(c_print) for (s = spring_list()) at_wall(s[0], s[1])
        translate([-(pcb_clear + spr_pre), -spr_w/2, 0.59]) cube([pcb_clear + spr_pre + 0.01, spr_w, 0.4]);
}

// =====================================================================
// Данные для сборки (assembly.scad подключает этот файл через use <...>)
// =====================================================================
function mount_board_z(r) = zp_of(r);
function mount_top_z(r)   = ztop_of(r);
function mount_len()      = oy - y_back;          // полная длина вдоль пальца
function mount_back()     = -y_back;              // от центра платы до торца у кисти
function mount_front()    = oy;                   // от центра платы до торца у кончика
function mount_width()    = 2*ox;
function mount_half_w()   = ox;
function mount_low_z(r)   = wing_k*r;             // низ щёк
function mount_exit(r)    = [hx, y_back - 0.5, zwire_of(r)];   // где жгут выходит к кисти
function mount_yr()       = yr;
function mount_mode()     = M;
function mount_dip_gap()  = dip_gap;
function mount_strap_y()  = [ys0, ys1];
function mount_tip_style() = TS;
function mount_overhang(dl) = oy - y_tip(dl);     // насколько держатель выходит за кончик пальца

// Метизы и пена (только для картинок)
module mount_hardware(r = finger_r, cover = true) {
    zp = zp_of(r);
    for (h = holes) color(c_metal) translate([h[0], h[1], zp - xtal_rec - nut_skin - nut_h]) cylinder(d = nut_af/cos(30), h = nut_h, $fn = 6);
    // bent: винт M2×6 со стороны разъёма — головкой прямо на плату
    for (h = low_holes()) color(c_metal) translate([h[0], h[1], zp + bno_pcb]) {
        cylinder(d = 3.8, h = 1.3, $fn = 20);
        translate([0, 0, -6 + 0.01]) cylinder(d = 2, h = 6, $fn = 12);
    }
    if (cover) {
        for (h = cov_holes()) color(c_metal) translate([h[0], h[1], zseat_of(r)]) {
            cylinder(d = 3.8, h = 1.3, $fn = 20);
            translate([0, 0, -10 + 0.01]) cylinder(d = 2, h = 10, $fn = 12);
        }
        color(c_foam) for (sx = [-1, 1]) translate([sx > 0 ? ledge_in : -ox + cov_t, -5.5, zst_of(r) - 0.6])
            cube([ox - cov_t - ledge_in, 9.5, 0.6]);
        if (m_str(M)) color(c_foam) translate([-ox + cov_t, ycb0, zht_of(r) + slv_top]) cube([2*(ox - cov_t), yhw0 - ycb0, 1.4]);
        if (m_bent(M)) color(c_foam) translate([hx - 4.6, yr + bent_gap + 1.0, zhax_of(r) + dup_w/2])
            cube([9.2, dup_l - 2.0, foam_loop]);
    }
}

// bent: провода выходят из корпуса к кончику, петлёй R2 поднимаются и идут над корпусом к кисти
module bent_loop_wires(r, lead = 2) {
    z0 = zhax_of(r);
    for (i = [0:3]) color(c_wires4[i]) translate([hx + (i - 1.5)*pitch, 0, 0]) {
        translate([0, yhe - 0.01, z0]) rotate([-90, 0, 0]) cylinder(d = wire_d, h = 0.81, $fn = 10);
        translate([0, yhe + 0.8, z0 + loop_r]) rotate([0, 90, 0])
            rotate_extrude(angle = 180, $fn = 24) translate([loop_r, 0]) circle(d = wire_d, $fn = 10);
        translate([0, y_back - lead, z0 + 2*loop_r]) rotate([-90, 0, 0]) cylinder(d = wire_d, h = yhe + 0.8 - y_back + lead, $fn = 10);
    }
}

// Плата с разъёмом (и насадкой) — в рабочем положении
module mount_board(r = finger_r, wires = true, lead = 2) {
    translate([0, 0, zp_of(r)]) bno055(true, true, -90, lead, wires && !m_bent(M), M, 90);
    if (m_str(M)) translate([hx, yr, zht_of(r)]) dupont_sleeve();
    if (m_bent(M) && wires) bent_loop_wires(r, lead);
}

// Держатель в сборе. cut = true — крышка разрезана по оси, чтобы было видно разъём
module finger_mount_full(r = finger_r, dl = finger_dl, cover = true, cut = false, wires = true, n = 0) {
    mount_base(r, dl);
    mount_board(r, wires);
    mount_hardware(r, cover);
    if (TS == "thimble") finger_thimble(r); else strap_ring(r);
    if (cover) {
        if (cut) intersection() { mount_cover(r, n); translate([0, -60, -1]) cube([100, 120, 100]); }
        else mount_cover(r, n);
    }
}

module finger_mount(r = finger_r, dl = finger_dl) { mount_base(r, dl); }

// ---------- Демонстрация: средняя + ногтевая фаланга, держатель в сборе ----------
module demo() {
    r = R;
    color([0.93, 0.76, 0.64]) {
        // ногтевая фаланга: от сустава DIP до кончика
        translate([0, y_dip, 0]) rotate([-90, 0, 0]) hull() {
            sphere(r + 0.3, $fn = 60);
            translate([0, 0, DL - r*0.9]) sphere(r*0.9, $fn = 60);
        }
        translate([0, y_dip - 26, 0]) rotate([-90, 0, 0]) cylinder(r = r + 0.6, h = 26, $fn = 60);
    }
    finger_mount_full(r, DL, true, true, true, num);
}

echo(str("FINGER MOUNT [", M, ", ", TS, ", ", variant, " R", R, "]: ", 2*ox, " x ", oy - y_back, " мм, верх над осью пальца ", ztop_of(R),
         " (над верхом пальца ", ztop_of(R) - R, "), низ платы ", zp_of(R) - R, " над пальцем; основание ",
         zst_of(R) - wing_k*R, " мм, крышка ", ztop_of(R) - zst_of(R), " мм высотой; ногтевая фаланга ", DL,
         " мм, вынос за кончик ", mount_overhang(DL), " мм; язычки ", [for (s = spring_list(R)) s[2]]));

// =====================================================================
if (part == "base") translate([0, 0, -wing_k*R]) mount_base(R, DL);
else if (part == "cover") translate([0, 0, -zst_of(R)]) mount_cover(R, num);
else if (part == "thimble") color(c_tpu) linear_extrude(th_len) thimble2d(R);
else if (part == "sleeve") translate([0, 0, slv_top]) rotate([180, 0, 0]) dupont_sleeve();
else if (part == "jig") pin_jig();
else if (part == "gauge") fit_gauge();
else demo();
