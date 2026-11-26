use crate::motion::Motion;

pub const GESTURES: [(&str, &str); 12] = [
    ("tap_1", "Тап большим"),
    ("tap_2", "Тап указательным"),
    ("tap_3", "Тап средним"),
    ("tap_4", "Тап безымянным"),
    ("tap_5", "Тап мизинцем"),
    ("lift_2", "Тап указательным вверх"),
    ("snap", "Щелчок большим и средним"),
    ("motion", "Движение одним пальцем"),
    ("scroll_up", "Взмах кистью вверх"),
    ("scroll_down", "Взмах кистью вниз"),
    ("thumb_index", "Удержание большого и указательного"),
    ("thumb_middle", "Удержание большого и среднего"),
];

#[derive(Default)]
struct Tap {
    start: Option<u32>,
    peak: f64,
    neutral: bool,
}

impl Tap {
    fn feed(&mut self, angle: f64, stamp: u32) -> Option<bool> {
        let size = angle.abs();
        if size <= 7. {
            self.neutral = true;
            return self
                .start
                .take()
                .filter(|start| (45..=300).contains(&stamp.wrapping_sub(*start)))
                .filter(|_| (15. ..=56.).contains(&self.peak.abs()))
                .map(|_| self.peak > 0.);
        }
        if self.neutral && size >= 10. {
            self.start = Some(stamp);
            self.peak = angle;
            self.neutral = false;
        } else if self.start.is_some() && size > self.peak.abs() {
            self.peak = angle;
        }
        None
    }
}

#[derive(Default)]
pub struct Gestures {
    taps: [Tap; 5],
    previous: Option<u32>,
    thumb: Option<u32>,
    middle: Option<u32>,
    pending: Option<u32>,
    last_snap: Option<u32>,
    last_tap: [Option<u32>; 5],
}

impl Gestures {
    pub fn feed(&mut self, stamp: u32, motion: &Motion, audio: Option<bool>) -> Option<usize> {
        let (Some(rates), Some(up)) = (motion.rates, motion.palm_up()) else {
            *self = Self::default();
            return None;
        };
        let (gyro, accel) = rates[0];
        let angles: [f64; 5] = std::array::from_fn(|i| {
            motion.directions[i + 1].map_or(0., |direction| {
                (-direction.dot(up)).clamp(-1., 1.).asin().to_degrees()
            })
        });
        let angular: [f64; 5] =
            std::array::from_fn(|i| (rates[i + 1].0 - gyro).length().to_degrees());
        let impulse: [f64; 5] = std::array::from_fn(|i| (rates[i + 1].1 - accel).length());
        let quiet = gyro.length().to_degrees() < 140. && accel.length() < 4.5;
        if self
            .previous
            .is_some_and(|last| stamp.wrapping_sub(last) > 85)
        {
            *self = Self::default();
        }
        self.previous = Some(stamp);
        let mut result = None;
        let mut count = 0;
        for (i, (tap, angle)) in self.taps.iter_mut().zip(angles).enumerate() {
            if let Some(down) = tap.feed(angle, stamp)
                && (down || i == 1)
                && self.last_tap[i].is_none_or(|last| stamp.wrapping_sub(last) >= 85)
            {
                result = Some((i, if down { i } else { 5 }));
                count += 1;
            }
        }
        if quiet
            && self
                .last_snap
                .is_none_or(|last| stamp.wrapping_sub(last) >= 700)
        {
            if angular[0] >= 175. {
                self.thumb = Some(stamp);
            }
            if angular[2] >= 330. && angles[2] >= 14. && impulse[2] >= 1.8 {
                self.middle = Some(stamp);
            }
            if self
                .thumb
                .is_some_and(|time| stamp.wrapping_sub(time) <= 75)
                && self
                    .middle
                    .is_some_and(|time| stamp.wrapping_sub(time) <= 75)
            {
                self.pending = Some(stamp);
                self.thumb = None;
                self.middle = None;
            }
        }
        if let Some(since) = self.pending {
            if stamp.wrapping_sub(since) > 100 {
                self.pending = None;
            } else if audio != Some(false) {
                self.pending = None;
                self.last_snap = Some(stamp);
                self.taps = Default::default();
                return Some(6);
            } else {
                return None;
            }
        }
        if self
            .last_snap
            .is_some_and(|last| stamp.wrapping_sub(last) < 220)
            || count != 1
        {
            return None;
        }
        result.map(|(i, gesture)| {
            self.last_tap[i] = Some(stamp);
            gesture
        })
    }
}
