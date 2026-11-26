use crate::protocol::{ALL, CALIBRATING, CHANNELS, Frame, Sample};
use glam::{DMat3, DVec3 as V};

pub const GRAVITY: f64 = 9.80665;
pub const SPREAD: [f64; 5] = [-40., -8., 0., 8., 15.];

#[derive(Clone, Copy, PartialEq, Eq, Default)]
pub enum Calibration {
    #[default]
    Idle,
    Collecting,
    Ready,
    Partial,
    Failed,
}

#[derive(Clone, Copy, Debug, Default)]
pub struct Action {
    pub dx: f64,
    pub dy: f64,
    pub wheel: i32,
    pub click: Option<bool>,
}

fn vector(values: [i16; 3]) -> V {
    V::from_array(values.map(f64::from))
}
fn transform(rows: [V; 3], value: V) -> V {
    DMat3::from_cols(rows[0], rows[1], rows[2]).transpose() * value
}

#[derive(Clone, Copy)]
struct Pose {
    reference: DMat3,
    rows: [V; 3],
    bias: V,
}

impl Pose {
    fn new(accel: V, gyro: V, mag: V) -> Self {
        let up = accel.normalize();
        let fallback = if up.x.abs() < 0.9 { V::X } else { V::Y };
        let east = up
            .cross(mag)
            .try_normalize()
            .unwrap_or_else(|| up.cross(fallback).normalize());
        let rows = [east.cross(up), east, up];
        Self {
            reference: DMat3::from_cols(rows[0], rows[1], rows[2]),
            rows,
            bias: gyro,
        }
    }

    fn direction(self, neutral: V) -> V {
        transform(self.rows, self.reference * neutral)
    }

    fn update(&mut self, sample: Sample, dt: f64) -> (V, V) {
        let mut gyro = (vector(sample.gyro) - self.bias) * (1f64.to_radians() / 16.);
        let speed = gyro.length();
        let [mut heading, _, mut up] = self.rows;
        if speed < 1.3f64.to_radians() {
            gyro = V::ZERO;
        } else if dt > 0. {
            let rotate = DMat3::from_axis_angle(gyro / speed, -speed * dt);
            heading = rotate * heading;
            up = rotate * up;
        }
        let accel = vector(sample.accel) / 100.;
        if (accel.length() - GRAVITY).abs() < 1. {
            let measured = accel.normalize();
            if up.dot(measured) > 0.3 {
                up = up.lerp(measured, 1. - (-dt / 0.30).exp()).normalize();
            }
        }
        let east = up.cross(heading).normalize();
        self.rows = [east.cross(up), east, up];
        (
            transform(self.rows, gyro),
            transform(self.rows, accel) - V::Z * GRAVITY,
        )
    }
}

#[derive(Clone, Copy, Default)]
struct Window {
    start: u32,
    count: u32,
    first: V,
    sums: [V; 3],
}

impl Window {
    fn feed(&mut self, sample: Option<Sample>, stamp: u32) {
        let Some(sample) = sample else {
            *self = Self::default();
            return;
        };
        let accel = vector(sample.accel);
        let gyro = vector(sample.gyro);
        if accel.length() <= 850. || accel.length() >= 1100. || gyro.length() > 128. {
            *self = Self::default();
            return;
        }
        if self.count > 0 && accel.distance(self.first) > 75. {
            *self = Self::default();
        }
        if self.count == 0 {
            self.start = stamp;
            self.first = accel;
        }
        self.count += 1;
        self.sums[0] += accel;
        self.sums[1] += gyro;
        self.sums[2] += vector(sample.mag);
    }

    fn pose(self, stamp: u32) -> Option<Pose> {
        (self.count >= 4 && stamp.wrapping_sub(self.start) >= 750).then(|| {
            let [accel, gyro, mag] = self.sums.map(|sum| sum / f64::from(self.count));
            Pose::new(accel, gyro, mag)
        })
    }
}

#[derive(Default)]
struct PointerGestures {
    candidate: Option<u8>,
    since: u32,
    scroll_at: Option<u32>,
    scroll_ready: bool,
    click_sent: bool,
    click_blocked: bool,
}

pub type Rates = [(V, V); CHANNELS];

pub struct Motion {
    poses: [Option<Pose>; CHANNELS],
    pub directions: [Option<V>; CHANNELS],
    pub extended: [Option<bool>; 5],
    forward: V,
    right: V,
    last_stamp: Option<u32>,
    valid: u8,
    windows: [Window; CHANNELS],
    calibration_start: Option<u32>,
    pub calibration: Calibration,
    pub rates: Option<Rates>,
    pointer: PointerGestures,
}

impl Default for Motion {
    fn default() -> Self {
        Self {
            poses: [None; CHANNELS],
            directions: [None; CHANNELS],
            extended: [None; 5],
            forward: V::Y,
            right: V::X,
            last_stamp: None,
            valid: 0,
            windows: [Window::default(); CHANNELS],
            calibration_start: None,
            calibration: Calibration::Idle,
            rates: None,
            pointer: PointerGestures::default(),
        }
    }
}

impl Motion {
    pub fn calibrate(&mut self) {
        *self = Self {
            calibration: Calibration::Collecting,
            ..Self::default()
        };
    }

    pub fn ready(&self) -> bool {
        self.calibration == Calibration::Ready && self.valid == ALL
    }

    pub fn palm_up(&self) -> Option<V> {
        Some(self.poses[0]?.direction(V::Z))
    }

    pub fn align_heading(&mut self) -> bool {
        let Some(palm) = self.poses[0] else {
            return false;
        };
        let mut direction = palm.reference.transpose() * palm.rows[2];
        direction.z = 0.;
        if direction.length() < 0.25 {
            return false;
        }
        self.forward = direction.normalize();
        self.right = self.forward.cross(V::Z);
        self.pointer = PointerGestures::default();
        true
    }

    fn collect(&mut self, frame: Frame) {
        if frame.flags & CALIBRATING != 0 {
            self.calibrate();
            return;
        }
        let start = *self.calibration_start.get_or_insert(frame.millis);
        for (window, sample) in self.windows.iter_mut().zip(frame.samples) {
            window.feed(sample, frame.millis);
        }
        if frame.millis.wrapping_sub(start) < 1250 {
            return;
        }
        self.poses = self.windows.map(|window| window.pose(frame.millis));
        let Some(palm) = self.poses[0] else {
            self.calibration = Calibration::Failed;
            return;
        };
        let mut forward = palm.reference.transpose() * V::Y;
        let horizontal = forward.z.abs() < 0.9;
        forward.z = 0.;
        self.forward = if horizontal {
            forward.try_normalize().unwrap_or(V::Y)
        } else {
            V::Y
        };
        self.right = self.forward.cross(V::Z);
        self.calibration = if self.poses.iter().all(Option::is_some) {
            Calibration::Ready
        } else {
            Calibration::Partial
        };
    }

    pub fn feed(&mut self, frame: Frame, sensitivity: f64) -> Action {
        self.valid = frame.valid();
        self.rates = None;
        if self.calibration == Calibration::Collecting {
            self.collect(frame);
        }
        let elapsed = self
            .last_stamp
            .replace(frame.millis)
            .map_or(0, |previous| frame.millis.wrapping_sub(previous));
        if elapsed > 350 || frame.flags & CALIBRATING != 0 {
            if matches!(self.calibration, Calibration::Ready | Calibration::Partial) {
                *self = Self::default();
            }
            return Action::default();
        }
        let dt = f64::from(elapsed) / 1000.;
        self.directions = [None; CHANNELS];
        let mut rates = [(V::ZERO, V::ZERO); CHANNELS];
        for (channel, (sample, rate)) in frame.samples.into_iter().zip(&mut rates).enumerate() {
            if let (Some(mut pose), Some(sample)) = (self.poses[channel], sample) {
                *rate = pose.update(sample, dt);
                self.poses[channel] = Some(pose);
                let mut neutral = self.forward;
                if channel > 0 {
                    let spread = SPREAD[channel - 1].to_radians();
                    neutral = self.forward * spread.cos() + self.right * spread.sin();
                    let angle: f64 = if self.extended[channel - 1] == Some(true) {
                        42.
                    } else {
                        27.
                    };
                    self.extended[channel - 1] = self.poses[0].map(|palm| {
                        pose.direction(neutral).dot(palm.direction(neutral))
                            >= angle.to_radians().cos()
                    });
                }
                self.directions[channel] = Some(pose.direction(neutral));
            } else {
                if self.poses[channel].take().is_some() {
                    self.calibration = Calibration::Partial;
                }
                if channel > 0 {
                    self.extended[channel - 1] = None;
                }
            }
        }
        if !self.ready() {
            self.pointer = PointerGestures::default();
            return Action::default();
        }
        self.rates = Some(rates);
        self.gesture(frame.millis, dt, rates, sensitivity)
    }

    fn gesture(&mut self, stamp: u32, dt: f64, rates: Rates, sensitivity: f64) -> Action {
        let fingers = self
            .extended
            .iter()
            .enumerate()
            .fold(0u8, |mask, (i, straight)| {
                mask | (u8::from(*straight == Some(true)) << (i + 1))
            });
        let state = &mut self.pointer;
        if state.candidate != Some(fingers) {
            *state = PointerGestures {
                candidate: Some(fingers),
                since: stamp,
                scroll_at: state.scroll_at,
                ..PointerGestures::default()
            };
        }
        let age = stamp.wrapping_sub(state.since);
        if age < 80 {
            return Action::default();
        }
        if fingers.count_ones() == 1 {
            let channel = fingers.trailing_zeros() as usize;
            let (gyro, linear) = rates[channel];
            let velocity = gyro.cross(self.directions[channel].unwrap_or(V::ZERO));
            let (mut x, mut y) = (velocity.dot(self.right) * 950., -velocity.z * 950.);
            if linear.length() > 2.2 {
                x += linear.dot(self.right) * 50.;
                y -= linear.z * 50. + linear.dot(self.forward) * 28.;
            }
            return Action {
                dx: (x * dt * sensitivity).clamp(-140., 140.),
                dy: (y * dt * sensitivity).clamp(-140., 140.),
                ..Action::default()
            };
        }
        if fingers.count_ones() >= 2 {
            let vertical = rates[0].1.z;
            if vertical.abs() < 1.1 {
                state.scroll_ready = true;
            }
            if vertical.abs() >= 2.6 {
                state.click_blocked = true;
                if state.scroll_ready
                    && state
                        .scroll_at
                        .is_none_or(|last| stamp.wrapping_sub(last) >= 450)
                {
                    state.scroll_ready = false;
                    state.scroll_at = Some(stamp);
                    return Action {
                        wheel: if vertical > 0. { 1 } else { -1 },
                        ..Action::default()
                    };
                }
            }
            if matches!(fingers, 6 | 10) && age >= 260 && !state.click_sent && !state.click_blocked
            {
                state.click_sent = true;
                return Action {
                    click: Some(fingers == 10),
                    ..Action::default()
                };
            }
        }
        Action::default()
    }
}
