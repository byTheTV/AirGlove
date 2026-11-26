use crate::{
    motion::{GRAVITY, SPREAD},
    protocol::{ALL, BATTERY_LOW, Frame, Sample},
};
use glam::{DMat3 as M, DVec3 as V};

pub const PRACTICE: [i32; 10] = [3, 3, 2, 5, 4, 4, 4, 5, -2, 1];
pub const KEYS: [&str; 10] = ["W", "W", "Q", "R", "E", "E", "E", "R", "F", "D"];
pub const PRACTICE_FRAMES: u32 = 380;
pub const SECTIONS: [&str; 10] = [
    "Нейтральная поза",
    "Движение курсора",
    "Тычок",
    "Прокрутка вверх",
    "Прокрутка вниз",
    "Левый клик",
    "Правый клик",
    "Кулак",
    "Обрыв датчика",
    "Возврат датчика",
];
const POSES: [[f64; 5]; 10] = [
    [0.; 5],
    [72., 0., 72., 72., 72.],
    [72., 0., 72., 72., 72.],
    [72., 0., 0., 72., 72.],
    [72., 0., 0., 72., 72.],
    [0., 0., 72., 72., 72.],
    [0., 72., 0., 72., 72.],
    [72.; 5],
    [0.; 5],
    [0.; 5],
];
const SNAP: f64 = 6.25;

fn hump(time: f64, start: f64, duration: f64) -> f64 {
    let fraction = (time - start) / duration;
    if (0. ..1.).contains(&fraction) {
        (std::f64::consts::PI * fraction).sin().powi(2)
    } else {
        0.
    }
}

fn matrices(time: f64, practice: bool) -> [M; 6] {
    let (palm, angles) = if practice {
        let mut angles = [0.; 5];
        for (i, finger) in PRACTICE.into_iter().enumerate() {
            angles[finger.unsigned_abs() as usize - 1] +=
                f64::from(finger.signum()) * 30. * hump(time, 1.65 + i as f64 * 0.40, 0.24);
        }
        angles[0] += 36. * hump(time, SNAP, 0.22);
        angles[2] += 72. * hump(time, SNAP + 0.02, 0.29);
        (M::IDENTITY, angles)
    } else {
        let (phase, local) = phase(time);
        let blend = (local / 0.45).min(1.);
        let blend = blend * blend * (3. - 2. * blend);
        let (yaw, pitch) = if matches!(phase, 1 | 7) {
            (
                35f64.to_radians() * hump(local, 0.8, 1.45),
                16f64.to_radians() * hump(local, 0.57, 0.8),
            )
        } else {
            (0., 0.)
        };
        (
            M::from_rotation_z(yaw) * M::from_rotation_x(pitch),
            std::array::from_fn(|i| {
                POSES[(phase + 9) % 10][i] * (1. - blend) + POSES[phase][i] * blend
            }),
        )
    };
    std::array::from_fn(|channel| {
        if channel == 0 {
            return palm;
        }
        let i = channel - 1;
        let spread = SPREAD[i].to_radians();
        palm * M::from_rotation_z(-spread)
            * M::from_rotation_x(-angles[i].to_radians())
            * M::from_rotation_z(spread)
            * M::from_rotation_z((12. * i as f64).to_radians())
    })
}

fn phase(seconds: f64) -> (usize, f64) {
    let local = seconds % 25.;
    ((local / 2.5) as usize, local % 2.5)
}

pub fn frame(index: u32, practice: bool) -> Frame {
    let seconds = f64::from(index) / 50.;
    let (phase, local) = phase(seconds);
    let current = matrices(seconds, practice);
    let previous = matrices((seconds - 0.02).max(0.), practice);
    let missing = !practice && phase == 8;
    let base = V::Z * GRAVITY;
    let samples = std::array::from_fn(|channel| {
        if missing && channel == 4 {
            return None;
        }
        let mut accel = base;
        if practice && channel == 3 {
            accel.x = 5. * hump(seconds, SNAP + 0.045, 0.12);
        } else if !practice && phase == 2 && channel == 2 {
            let pulse = 4. * (hump(local, 1., 0.22) - hump(local, 1.22, 0.22));
            accel += V::new(pulse, pulse, 0.);
        } else if !practice && matches!(phase, 3 | 4) {
            accel.z += (if phase == 3 { 4. } else { -4. })
                * (hump(local, 1., 0.24) - hump(local, 1.25, 0.24));
        }
        let old = previous[channel];
        let new = current[channel];
        let omega = old.x_axis.cross(new.x_axis)
            + old.y_axis.cross(new.y_axis)
            + old.z_axis.cross(new.z_axis);
        let axes = new.transpose();
        let quantize = |vector: V| {
            vector
                .to_array()
                .map(|value| value.round_ties_even() as i16)
        };
        Some(Sample {
            accel: quantize((axes * accel) * 100.),
            gyro: quantize((axes * omega) * (25. * 1f64.to_degrees() * 16.)),
            mag: quantize(axes * V::new(450., 0., 275.)),
        })
    });
    Frame {
        sequence: index as u16,
        millis: index.wrapping_mul(20),
        samples,
        biased: if missing { ALL ^ 16 } else { ALL },
        flags: if missing { BATTERY_LOW } else { 0 },
        battery_mv: if missing { 3320 } else { 3900 },
    }
}

#[derive(Default)]
pub struct Training {
    pub progress: usize,
    pub errors: usize,
    pub duration: Option<f64>,
    start: Option<f64>,
}

impl Training {
    pub fn feed(&mut self, key: &str, seconds: f64) {
        if self.duration.is_some() {
            return;
        }
        if key != KEYS[self.progress] {
            self.errors += 1;
            self.progress = 0;
            self.start = None;
            if key != KEYS[0] {
                return;
            }
        }
        let start = *self.start.get_or_insert(seconds);
        self.progress += 1;
        if self.progress == KEYS.len() {
            self.duration = Some(seconds - start);
        }
    }
}
