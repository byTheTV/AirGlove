#!/usr/bin/env bash
# Пересборка всех STL и картинок для трёх способов подключения.
# Запуск из папки tools/model:  OPENSCAD=/путь/к/openscad ./build_all.sh [режим ...]
# Без аргументов — все три режима. Результат: docs/model/<режим>/stl/*.stl и docs/model/<режим>/*.png
set -e
OS=${OPENSCAD:-openscad}
MODES=${*:-"dupont_straight dupont_bent soldered_stubs"}
ONLY=${ONLY:-all}   # ONLY=png — только картинки, ONLY=stl — только STL
R="--imgsize=1800,1300 --colorscheme=Tomorrow"

for M in $MODES; do
    D=../../docs/model/$M
    O=$D/stl
    mkdir -p "$O"
    if [ "$ONLY" != png ]; then
    rm -f "$O"/*.stl
    stl() { out=$1; shift; "$OS" -o "$O/$out" -D "conn_mode=\"$M\"" "$@" 2>&1 | grep -E "^(ECHO|ERROR|WARNING)" || true; }
    stl finger_mount.stl       -D "part=\"base\""   finger_mount.scad
    stl finger_mount_pinky.stl -D "part=\"base\""   -D "variant=\"pinky\"" finger_mount.scad
    stl finger_mount_thumb.stl -D "part=\"base\""   -D "variant=\"thumb\"" finger_mount.scad
    for n in 1 2 3 4 5; do
        stl finger_cover_$n.stl -D "part=\"cover\"" -D num=$n finger_mount.scad
    done
    stl fit_gauge.stl          -D "part=\"gauge\""  finger_mount.scad
    stl pod_base.stl           -D "part=\"base\""   pod.scad
    stl pod_lid.stl            -D "part=\"lid\""    pod.scad
    stl wrist_box.stl          -D "part=\"base\""   wrist_box.scad
    stl wrist_box_lid.stl      -D "part=\"lid\""    wrist_box.scad
    case $M in
        dupont_straight) stl dupont_sleeve.stl -D "part=\"sleeve\"" finger_mount.scad ;;
        dupont_bent)     stl pin_bend_jig.stl  -D "part=\"jig\""    finger_mount.scad
                         stl pod_deck.stl      -D "part=\"deck\""   pod.scad ;;
        soldered_stubs)  stl pin_cut_jig.stl   -D "part=\"jig\""    finger_mount.scad ;;
    esac
    fi
    [ "$ONLY" = stl ] && continue

    png() { out=$1; shift; "$OS" -o "$D/$out" $R -D "conn_mode=\"$M\"" "$@" 2>&1 | grep -E "^(ERROR|WARNING)" || true; }
    png assembly_persp.png     --camera=-420,120,400,0,25,0 assembly.scad
    png assembly_top.png       --projection=o --camera=0,-25,0,0,0,90,760 assembly.scad
    png finger_closeup.png     --camera=-120,-105,85,0,-12,16 -D "view=\"closeup\"" assembly.scad
    case $M in   # центр и расстояние камеры подобраны под высоту деталей режима
        dupont_straight) CP=0,0,48,58,0,40,340; CW=0,20,30,55,0,35,340 ;;
        dupont_bent)     CP=0,0,40,58,0,40,315; CW=0,15,22,55,0,35,270 ;;
        soldered_stubs)  CP=0,0,16,58,0,40,220; CW=0,12,20,55,0,35,240 ;;
    esac
    png pod_exploded.png       --camera=$CP -D explode=true assembly.scad
    png wrist_box_exploded.png --camera=$CW -D "view=\"wrist_exploded\"" assembly.scad
done
