use cpal::{
    FromSample, Sample, SampleFormat, SizedSample,
    traits::{DeviceTrait, HostTrait, StreamTrait},
};
use std::{
    collections::VecDeque,
    error::Error,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};

struct Transients {
    peak: f32,
    events: VecDeque<Instant>,
    error: Option<String>,
}

impl Default for Transients {
    fn default() -> Self {
        Self {
            peak: 0.02,
            events: VecDeque::with_capacity(16),
            error: None,
        }
    }
}

impl Transients {
    fn feed<T: Sample>(&mut self, data: &[T], now: Instant)
    where
        f32: FromSample<T>,
    {
        if data.is_empty() {
            return;
        }
        let (peak, squares) = data.iter().fold((0f32, 0f32), |(peak, squares), sample| {
            let value = sample.to_sample::<f32>();
            (peak.max(value.abs()), squares + value * value)
        });
        let rms = (squares / data.len() as f32).sqrt();
        if peak >= (self.peak * 2.8).max(0.06) && peak >= 3.2 * rms {
            if self.events.len() == 16 {
                self.events.pop_front();
            }
            self.events.push_back(now);
        }
        self.peak = 0.88 * self.peak + 0.12 * peak;
    }
}

pub struct Microphone {
    _stream: cpal::Stream,
    state: Arc<Mutex<Transients>>,
}

impl Microphone {
    pub fn open() -> Result<Self, Box<dyn Error>> {
        let device = cpal::default_host()
            .default_input_device()
            .ok_or("Микрофон не найден")?;
        let config = device.default_input_config()?;
        let state = Arc::new(Mutex::new(Transients::default()));
        let settings = config.config();
        let stream = match config.sample_format() {
            SampleFormat::F32 => open::<f32>(&device, &settings, &state)?,
            SampleFormat::I16 => open::<i16>(&device, &settings, &state)?,
            SampleFormat::I32 => open::<i32>(&device, &settings, &state)?,
            SampleFormat::U16 => open::<u16>(&device, &settings, &state)?,
            _ => return Err("Формат микрофона не поддерживается".into()),
        };
        stream.play()?;
        Ok(Self {
            _stream: stream,
            state,
        })
    }

    pub fn confirmed(&self, stamp: Instant) -> bool {
        self.state.lock().is_ok_and(|state| {
            state.events.iter().any(|&event| {
                stamp
                    .saturating_duration_since(event)
                    .max(event.saturating_duration_since(stamp))
                    <= Duration::from_millis(110)
            })
        })
    }

    pub fn error(&self) -> Option<String> {
        self.state.lock().ok()?.error.clone()
    }
}

fn open<T: SizedSample>(
    device: &cpal::Device,
    config: &cpal::StreamConfig,
    state: &Arc<Mutex<Transients>>,
) -> Result<cpal::Stream, cpal::BuildStreamError>
where
    f32: FromSample<T>,
{
    let capture = state.clone();
    let errors = state.clone();
    device.build_input_stream(
        config,
        move |data: &[T], _| {
            if let Ok(mut state) = capture.lock() {
                state.feed(data, Instant::now());
            }
        },
        move |error| {
            if let Ok(mut state) = errors.lock() {
                state.error = Some(error.to_string());
            }
        },
        None,
    )
}
