use super::{ACCENT, BACK, MUTED, WARNING};
use crate::app::AirGlove;
use eframe::egui::{Color32, Mesh, Painter, Pos2, Sense, Shape, Stroke, Ui, Vec2, vec2};

pub(super) const HEIGHT: f32 = 234.;
const FABRIC: Color32 = Color32::from_rgb(25, 39, 53);
const LIGHT: Color32 = Color32::from_rgb(65, 87, 107);
const EDGE: Color32 = Color32::from_rgb(92, 116, 135);
const SEAM: Color32 = Color32::from_rgb(49, 66, 83);
const SOCKET: Color32 = Color32::from_rgb(21, 33, 45);

struct Finger {
    base: Vec2,
    tip: Vec2,
    width: f32,
    travel: Vec2,
}

const FINGERS: [Finger; 5] = [
    Finger {
        base: vec2(-39., 21.),
        tip: vec2(-75., -13.),
        width: 21.,
        travel: vec2(25., 20.),
    },
    Finger {
        base: vec2(-27., -26.),
        tip: vec2(-37., -89.),
        width: 20.,
        travel: vec2(7., 39.),
    },
    Finger {
        base: vec2(-5., -32.),
        tip: vec2(-7., -104.),
        width: 21.,
        travel: vec2(2., 46.),
    },
    Finger {
        base: vec2(17., -27.),
        tip: vec2(21., -92.),
        width: 19.,
        travel: vec2(-4., 42.),
    },
    Finger {
        base: vec2(36., -17.),
        tip: vec2(48., -64.),
        width: 16.,
        travel: vec2(-10., 33.),
    },
];

pub(super) fn channel_color(valid: Option<u8>, channel: usize) -> Color32 {
    match valid {
        Some(mask) if mask & (1 << channel) != 0 => ACCENT,
        Some(_) => WARNING,
        None => MUTED,
    }
}

pub(super) fn draw(app: &AirGlove, ui: &mut Ui) {
    let (bounds, _) =
        ui.allocate_exact_size(vec2(ui.available_width().max(1.), HEIGHT), Sense::hover());
    let painter = ui.painter_at(bounds.shrink(1.));
    painter.rect_filled(bounds, 8, BACK);
    let columns = (bounds.width() / 44.) as i32;
    for row in -5..=5 {
        for col in -columns..=columns {
            let point = bounds.center() + vec2(col as f32 * 22., row as f32 * 22.);
            if bounds.shrink(7.).contains(point) {
                painter.circle_filled(point, 0.8, Color32::from_rgb(47, 66, 80));
            }
        }
    }

    let scale = (bounds.width() / 190.).min(bounds.height() / 242.);
    let origin = bounds.center() + vec2(9., 7.) * scale;
    let palm_up = app.motion.palm_up();
    let rotation = palm_up.map_or(0., |up| (up.x as f32 * 0.3).clamp(-0.2, 0.2));
    let glove = Glove {
        painter: &painter,
        origin,
        scale,
        rotation: eframe::egui::emath::Rot2::from_angle(rotation),
    };
    let valid = app.latest.map(|frame| frame.valid());

    glove.cuff();
    let fingers: [FingerPose; 5] = std::array::from_fn(|i| {
        let finger = &FINGERS[i];
        let direction = app.motion.directions[i + 1];
        // Project finger pitch against the palm so rotating the whole wrist doesn't curl the fingers.
        let bend = match (direction, palm_up) {
            (Some(direction), Some(up)) => {
                ((-direction.dot(up) as f32 - 0.08) / 0.85).clamp(-0.15, 1.)
            }
            _ => 0.,
        };
        let tip = finger.tip + finger.travel * bend;
        let delta = tip - finger.base;
        let joint = finger.base + delta * 0.56 + vec2(bend * 1.5, 0.);
        FingerPose {
            base: finger.base,
            joint,
            tip,
            width: finger.width,
            bend,
        }
    });
    for finger in &fingers {
        glove.finger(finger);
    }
    glove.palm();
    for (&finger, channel) in fingers.iter().zip(1..) {
        let direction = (finger.tip - finger.joint).normalized();
        let healthy = valid.is_some_and(|mask| mask & (1 << channel) != 0);
        let highlight = healthy && app.motion.extended[channel - 1] == Some(true);
        glove.sensor(
            finger.tip - direction * 8.,
            direction,
            channel_color(valid, channel),
            highlight,
        );
    }
    glove.controller(
        channel_color(valid, 0),
        valid.is_some_and(|mask| mask & 1 != 0),
    );
}

#[derive(Clone, Copy)]
struct FingerPose {
    base: Vec2,
    joint: Vec2,
    tip: Vec2,
    width: f32,
    bend: f32,
}

struct Glove<'a> {
    painter: &'a Painter,
    origin: Pos2,
    scale: f32,
    rotation: eframe::egui::emath::Rot2,
}

impl Glove<'_> {
    fn at(&self, point: Vec2) -> Pos2 {
        self.origin + (self.rotation * point) * self.scale
    }

    fn line(&self, points: &[Vec2], width: f32, color: Color32) {
        self.painter.add(Shape::line(
            points.iter().map(|&point| self.at(point)).collect(),
            Stroke::new(width * self.scale, color),
        ));
    }

    fn surface(
        &self,
        center: Vec2,
        points: &[Vec2],
        dark: Color32,
        light: Color32,
        outline: Color32,
    ) {
        let mut mesh = Mesh::default();
        mesh.colored_vertex(self.at(center), dark.lerp_to_gamma(light, 0.55));
        for &point in points {
            let lighting =
                (0.58 - (point.x - center.x) / 72. - (point.y - center.y) / 160.).clamp(0.06, 1.);
            mesh.colored_vertex(self.at(point), dark.lerp_to_gamma(light, lighting));
        }
        for i in 0..points.len() as u32 {
            mesh.add_triangle(0, i + 1, (i + 1) % points.len() as u32 + 1);
        }
        self.painter.add(Shape::mesh(mesh));
        self.painter.add(Shape::closed_line(
            points.iter().map(|&point| self.at(point)).collect(),
            Stroke::new(1.05 * self.scale, outline),
        ));
    }

    fn cuff(&self) {
        let cuff = round(&[
            vec2(-27., 58.),
            vec2(32., 56.),
            vec2(34., 87.),
            vec2(27., 94.),
            vec2(-25., 94.),
            vec2(-32., 87.),
        ]);
        self.surface(vec2(0., 77.), &cuff, SOCKET, SEAM, EDGE);
        self.line(&[vec2(-27., 82.), vec2(30., 81.)], 1.5, EDGE);
        for x in [-20., -13., -6., 1., 8., 15., 22.] {
            self.line(&[vec2(x, 85.), vec2(x + 1., 89.)], 1., SEAM);
        }
    }

    fn palm(&self) {
        let palm = round(&[
            vec2(-49., 0.),
            vec2(-45., -17.),
            vec2(-34., -27.),
            vec2(-17., -30.),
            vec2(-6., -36.),
            vec2(9., -31.),
            vec2(24., -30.),
            vec2(37., -22.),
            vec2(47., -14.),
            vec2(49., 18.),
            vec2(45., 43.),
            vec2(33., 64.),
            vec2(26., 76.),
            vec2(-22., 76.),
            vec2(-28., 65.),
            vec2(-46., 38.),
            vec2(-51., 20.),
        ]);
        self.surface(vec2(0., 16.), &palm, FABRIC, LIGHT, EDGE);
        self.line(
            &[
                vec2(-39., -7.),
                vec2(-22., -16.),
                vec2(5., -21.),
                vec2(25., -17.),
                vec2(39., -9.),
            ],
            1.1,
            SEAM,
        );
        self.line(
            &[vec2(-38., 14.), vec2(-32., 35.), vec2(-21., 50.)],
            1.2,
            SEAM,
        );
        self.line(&[vec2(38., 14.), vec2(34., 37.), vec2(25., 52.)], 1.2, SEAM);
        self.line(
            &[vec2(-22., 63.), vec2(-4., 66.), vec2(23., 62.)],
            1.2,
            SEAM,
        );
    }

    fn finger(&self, finger: &FingerPose) {
        let normal = |vector: Vec2| vector.rot90().normalized();
        let proximal = normal(finger.joint - finger.base);
        let between = normal(finger.tip - finger.base);
        let distal = normal(finger.tip - finger.joint);
        let width = finger.width * 0.5;
        let radius = width * 0.75;
        let mut points = vec![
            finger.base - proximal * width,
            finger.joint - between * width * 0.88,
        ];
        for step in 0..=8 {
            let angle = std::f32::consts::PI * step as f32 / 8.;
            let forward = (finger.tip - finger.joint).normalized();
            points.push(finger.tip + (forward * angle.sin() - distal * angle.cos()) * radius);
        }
        points.extend([
            finger.joint + between * width * 0.88,
            finger.base + proximal * width,
        ]);
        let bright = LIGHT.lerp_to_gamma(FABRIC, finger.bend.max(0.) * 0.45);
        self.surface(finger.joint, &points, FABRIC, bright, EDGE);
        self.line(
            &[
                finger.joint - between * width * 0.62,
                finger.joint + between * width * 0.62,
            ],
            1.,
            SEAM,
        );
    }

    fn sensor(&self, center: Vec2, direction: Vec2, led: Color32, highlight: bool) {
        let points = enclosure(center, direction, 16., 11., 2.5);
        let border = if highlight {
            ACCENT.gamma_multiply(0.80)
        } else {
            EDGE
        };
        self.surface(center, &points, SOCKET, SEAM, border);
        let lamp = self.at(center + direction * 3.2);
        if highlight {
            self.painter
                .circle_filled(lamp, 4.2 * self.scale, led.gamma_multiply(0.19));
        }
        self.painter.circle_filled(lamp, 2.1 * self.scale, led);
        let cross = direction.rot90();
        self.line(
            &[
                center - direction * 3.3 - cross * 2.2,
                center - direction * 3.3 + cross * 2.2,
            ],
            0.9,
            EDGE,
        );
    }

    fn controller(&self, led: Color32, active: bool) {
        let center = vec2(1., 26.);
        let points = enclosure(center, Vec2::Y, 39., 37., 6.);
        self.surface(center, &points, SOCKET, SEAM, EDGE);
        let inner = enclosure(center + vec2(0., -1.), Vec2::Y, 17., 17., 3.);
        self.surface(center, &inner, FABRIC, LIGHT, SEAM);
        for pin in [-5., 0., 5.] {
            self.line(
                &[center + vec2(-13., pin), center + vec2(-9., pin)],
                1.,
                EDGE,
            );
            self.line(&[center + vec2(9., pin), center + vec2(13., pin)], 1., EDGE);
        }
        let lamp = self.at(center + vec2(0., -12.));
        if active {
            self.painter
                .circle_filled(lamp, 5.2 * self.scale, led.gamma_multiply(0.19));
        }
        self.painter.circle_filled(lamp, 2.4 * self.scale, led);
        self.line(
            &[center + vec2(-5., 12.), center + vec2(5., 12.)],
            1.2,
            EDGE,
        );
    }
}

fn round(points: &[Vec2]) -> Vec<Vec2> {
    let mut result = Vec::with_capacity(points.len() * 2);
    for (&a, &b) in points.iter().zip(points.iter().cycle().skip(1)) {
        result.push(a + (b - a) * 0.18);
        result.push(a + (b - a) * 0.82);
    }
    result
}

fn enclosure(center: Vec2, axis: Vec2, length: f32, width: f32, corner: f32) -> [Vec2; 8] {
    let half = vec2(width, length) * 0.5;
    let cross = axis.rot90();
    [
        vec2(-half.x + corner, -half.y),
        vec2(half.x - corner, -half.y),
        vec2(half.x, -half.y + corner),
        vec2(half.x, half.y - corner),
        vec2(half.x - corner, half.y),
        vec2(-half.x + corner, half.y),
        vec2(-half.x, half.y - corner),
        vec2(-half.x, -half.y + corner),
    ]
    .map(|local| center + cross * local.x + axis * local.y)
}
