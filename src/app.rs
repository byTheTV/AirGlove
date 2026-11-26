use crate::{
    audio::Microphone,
    gestures::{GESTURES, Gestures},
    input::SystemInput,
    motion::{Action, Calibration, Motion},
    profiles::{Kind, Profile, Profiles},
    protocol::{ALL, Frame},
    simulation::Training,
    source::{Event, Source, Stream},
    view,
};
use eframe::egui;
use std::{
    collections::VecDeque,
    fs::File,
    io::{self, BufWriter, Write},
    time::{Duration, Instant},
};

pub const STALE: Duration = Duration::from_millis(350);

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Page {
    Monitor,
    Profiles,
    Training,
}

pub struct AirGlove {
    pub page: Page,
    pub source: Source,
    stream: Option<Stream>,
    pub status: String,
    pub message: String,
    pub motion: Motion,
    gestures: Gestures,
    pub profiles: Profiles,
    pub edit: Profile,
    pub delete_confirm: bool,
    pub training: Training,
    training_started: Instant,
    armed: bool,
    input: SystemInput,
    pub latest: Option<Frame>,
    pub lost: u64,
    pub received: VecDeque<Instant>,
    last_received: Option<Instant>,
    moving_at: Option<Instant>,
    pub cursor: [f32; 2],
    pub wheel: i32,
    pub last_gesture: String,
    pub activities: VecDeque<String>,
    pub sensitivity: f64,
    pub port: String,
    pub address: String,
    pub recording: Option<(BufWriter<File>, u64)>,
    pub ended: bool,
    pub mic_enabled: bool,
    mic: Option<Microphone>,
}

impl AirGlove {
    pub fn new(ctx: &egui::Context, source: Source) -> Self {
        let profiles = Profiles::load();
        let initial = profiles.current().clone();
        let mut app = Self {
            page: Page::Monitor,
            source: Source::Demo,
            stream: None,
            status: String::new(),
            message: String::new(),
            motion: Motion::default(),
            gestures: Gestures::default(),
            edit: initial,
            profiles,
            delete_confirm: false,
            training: Training::default(),
            training_started: Instant::now(),
            armed: false,
            input: SystemInput::default(),
            latest: None,
            received: VecDeque::new(),
            lost: 0,
            last_received: None,
            moving_at: None,
            cursor: [0.5; 2],
            wheel: 0,
            last_gesture: "Жесты пока не распознаны".into(),
            activities: VecDeque::new(),
            sensitivity: 1.,
            port: String::new(),
            address: String::new(),
            recording: None,
            ended: false,
            mic_enabled: false,
            mic: None,
        };
        if let Source::Usb(port) = &source {
            app.port.clone_from(port);
        }
        if let Source::Bluetooth(address) = &source {
            app.address.clone_from(address);
        }
        app.select(ctx, source);
        app
    }

    pub fn select(&mut self, ctx: &egui::Context, source: Source) {
        self.disarm();
        self.finish_record();
        self.stream = None;
        self.source = source.clone();
        self.ended = false;
        self.reset();
        self.status = "Подготовка источника…".into();
        self.refresh_mic();
        match Stream::start(source, ctx.clone()) {
            Ok(stream) => self.stream = Some(stream),
            Err(error) => {
                self.status = format!("Не удалось открыть источник · {error}");
                self.ended = true;
            }
        }
    }

    fn reset(&mut self) {
        self.motion = Motion::default();
        self.gestures = Gestures::default();
        self.latest = None;
        self.last_received = None;
        self.moving_at = None;
        self.received.clear();
        self.lost = 0;
        self.cursor = [0.5; 2];
        self.wheel = 0;
        self.activities.clear();
        self.last_gesture = "Жесты пока не распознаны".into();
        if !self.source.live() {
            self.motion.calibrate();
        }
    }

    pub fn refresh_mic(&mut self) {
        self.mic = None;
        if self.mic_enabled && self.source.live() {
            match Microphone::open() {
                Ok(mic) => self.mic = Some(mic),
                Err(error) => self.message = format!("Микрофон недоступен · {error}"),
            }
        }
    }

    pub fn armed(&self) -> bool {
        self.armed
    }

    pub fn can_arm(&self, now: Instant) -> bool {
        self.page == Page::Monitor
            && self.source.live()
            && !self.ended
            && self.motion.ready()
            && self
                .last_received
                .is_some_and(|stamp| now.saturating_duration_since(stamp) < STALE)
    }

    pub fn toggle_input(&mut self) {
        if self.armed {
            self.disarm();
        } else if self.can_arm(Instant::now()) && !SystemInput::escape() {
            self.armed = true;
            self.message = "Системный ввод включён. Esc отключает управление.".into();
        }
    }

    pub fn disarm(&mut self) {
        if self.armed {
            self.message = "Системный ввод отключён.".into();
        }
        self.armed = false;
        if let Err(error) = self.input.release(None) {
            self.message = error.to_string();
        }
    }

    fn input_failed(&mut self, error: io::Error) {
        self.disarm();
        self.message = error.to_string();
    }

    pub fn calibrate(&mut self, ctx: &egui::Context) {
        self.disarm();
        if self.ended && matches!(self.source, Source::Replay(_)) {
            self.select(ctx, self.source.clone());
        } else {
            self.motion.calibrate();
            self.gestures = Gestures::default();
            self.message = "Положите кисть горизонтально и выпрямите пальцы.".into();
        }
    }

    pub fn align(&mut self) {
        self.disarm();
        self.message = if self.motion.align_heading() {
            self.gestures = Gestures::default();
            "Направление кисти задано."
        } else {
            "Приподнимите выпрямленную кисть на 25–45° и повторите."
        }
        .into();
    }

    pub fn open_recording(&mut self, ctx: &egui::Context) {
        self.disarm();
        if let Some(path) = rfd::FileDialog::new()
            .set_title("Открыть запись AirGlove")
            .add_filter("Телеметрия", &["aglog", "txt", "log"])
            .pick_file()
        {
            self.select(ctx, Source::Replay(path));
        }
    }

    pub fn toggle_record(&mut self) {
        if self.recording.is_some() {
            self.finish_record();
            return;
        }
        self.disarm();
        let Some(mut path) = rfd::FileDialog::new()
            .set_title("Записать телеметрию")
            .set_file_name("AirGlove.aglog")
            .add_filter("Запись AirGlove", &["aglog"])
            .save_file()
        else {
            return;
        };
        if path.extension().is_none() {
            path.set_extension("aglog");
        }
        match File::options().write(true).create_new(true).open(path) {
            Ok(file) => {
                self.recording = Some((BufWriter::new(file), 0));
                self.message = "Запись началась.".into();
            }
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {
                self.message = "Файл уже существует. Выберите другое имя.".into()
            }
            Err(error) => self.message = format!("Ошибка записи · {error}"),
        }
    }

    fn finish_record(&mut self) {
        if let Some((mut output, count)) = self.recording.take() {
            self.message = match output.flush().and_then(|_| output.get_ref().sync_all()) {
                Ok(()) => format!("Запись сохранена · кадров {count}"),
                Err(error) => format!("Ошибка записи · {error}"),
            };
        }
    }

    pub fn set_page(&mut self, page: Page) {
        if self.page != page {
            self.disarm();
            self.page = page;
            self.delete_confirm = false;
        }
    }

    pub fn change_profile(&mut self, id: &str, persist: bool) {
        self.disarm();
        if persist {
            if let Err(error) = self.profiles.activate(id) {
                self.message = format!("Ошибка сохранения · {error}");
            }
        } else {
            self.profiles.preview(id);
        }
    }

    pub fn practice(&mut self, ctx: &egui::Context) {
        let id = self
            .profiles
            .data
            .profiles
            .iter()
            .find(|profile| profile.id == "invoker")
            .map(|profile| profile.id.clone());
        if let Some(id) = id {
            self.change_profile(&id, false);
        }
        self.training = Training::default();
        self.training_started = Instant::now();
        self.select(ctx, Source::Practice);
    }

    fn receive(&mut self, frame: Frame, stamp: Instant, now: Instant) {
        if now.saturating_duration_since(stamp) >= STALE {
            self.disarm();
            self.motion = Motion::default();
            self.gestures = Gestures::default();
            return;
        }
        if let Some(previous) = self.latest {
            let gap = frame.sequence.wrapping_sub(previous.sequence);
            if gap == 0 && frame.millis == previous.millis {
                return;
            }
            if (2..0x8000).contains(&gap) {
                self.lost += u64::from(gap - 1);
            }
        }
        if self
            .last_received
            .is_some_and(|last| stamp.saturating_duration_since(last) >= STALE)
        {
            self.disarm();
            if self.source.live() {
                self.motion = Motion::default();
                self.gestures = Gestures::default();
            }
        }
        self.latest = Some(frame);
        self.last_received = Some(stamp);
        self.received.push_back(stamp);
        if let Some((writer, count)) = &mut self.recording {
            match frame.write(writer) {
                Ok(()) => *count += 1,
                Err(error) => {
                    self.finish_record();
                    self.message = format!("Ошибка записи · {error}");
                }
            }
        }
        if matches!(self.source, Source::Demo)
            && !matches!(
                self.motion.calibration,
                Calibration::Collecting | Calibration::Ready
            )
            && frame.valid() == ALL
        {
            self.motion.calibrate();
        }
        let action = self.motion.feed(frame, self.sensitivity);
        if self.armed && !self.can_arm(now) {
            self.disarm();
        }
        let confirm = (self.mic_enabled && self.source.live())
            .then(|| self.mic.as_ref().is_some_and(|mic| mic.confirmed(stamp)));
        let gesture = self.gestures.feed(frame.millis, &self.motion, confirm);
        if self.page != Page::Profiles {
            self.route(gesture, action, stamp, now);
        }
    }

    fn route(&mut self, gesture: Option<usize>, action: Action, stamp: Instant, now: Instant) {
        if let Some(index) = gesture {
            self.dispatch(index, stamp, now);
            if index == 6 {
                return;
            }
        }
        let moving = action.dx.abs() + action.dy.abs() >= 1.;
        if self.profiles.current().binding("motion").action == Kind::Pointer {
            if action.dx != 0. || action.dy != 0. {
                self.apply(action, now);
            }
        } else if moving
            && self.moving_at.is_none_or(|last| {
                stamp.saturating_duration_since(last) >= Duration::from_millis(180)
            })
        {
            self.dispatch(7, stamp, now);
        }
        if moving {
            self.moving_at = Some(stamp);
        }
        if action.wheel != 0 {
            self.dispatch(if action.wheel > 0 { 8 } else { 9 }, stamp, now);
        }
        if let Some(right) = action.click {
            self.dispatch(if right { 11 } else { 10 }, stamp, now);
        }
    }

    pub fn dispatch(&mut self, index: usize, stamp: Instant, now: Instant) {
        let (key, label) = GESTURES[index];
        let binding = self.profiles.current().binding(key);
        if binding.action != Kind::None || index < 6 {
            self.last_gesture = format!("{label} → {}", binding.label());
        }
        match binding.action {
            Kind::Next => {
                if let Err(error) = self.input.release(None) {
                    self.input_failed(error);
                }
                self.moving_at = None;
                self.profiles.cycle();
                self.activity(self.profiles.current().name.clone(), true);
            }
            Kind::Key => {
                if self.page == Page::Training {
                    self.training.feed(
                        &binding.key,
                        stamp
                            .saturating_duration_since(self.training_started)
                            .as_secs_f64(),
                    );
                } else if self.armed
                    && self.can_arm(now)
                    && let Err(error) = self.input.tap(&binding.key, now)
                {
                    self.input_failed(error);
                }
                self.activity(binding.key, true);
            }
            Kind::Left | Kind::Right => self.apply(
                Action {
                    click: Some(binding.action == Kind::Right),
                    ..Action::default()
                },
                now,
            ),
            Kind::Up | Kind::Down => self.apply(
                Action {
                    wheel: if binding.action == Kind::Up { 1 } else { -1 },
                    ..Action::default()
                },
                now,
            ),
            _ => {}
        }
    }

    fn activity(&mut self, label: String, repeat: bool) {
        if !repeat && self.activities.back() == Some(&label) {
            return;
        }
        if self.activities.len() == 6 {
            self.activities.pop_front();
        }
        self.activities.push_back(label);
    }

    fn apply(&mut self, action: Action, now: Instant) {
        self.cursor[0] = (self.cursor[0] + action.dx as f32 / 750.).clamp(0.03, 0.97);
        self.cursor[1] = (self.cursor[1] + action.dy as f32 / 380.).clamp(0.05, 0.95);
        if let Some(right) = action.click {
            self.activity(if right { "ПКМ" } else { "ЛКМ" }.into(), true);
        }
        if action.wheel != 0 {
            self.wheel = self.wheel.saturating_add(action.wheel);
            self.activity(
                if action.wheel > 0 {
                    "Колесо ↑"
                } else {
                    "Колесо ↓"
                }
                .into(),
                true,
            );
        }
        if action.dx.abs() + action.dy.abs() >= 0.75 {
            self.activity("Движение".into(), false);
        }
        if self.armed
            && self.can_arm(now)
            && let Err(error) = self.input.apply(action)
        {
            self.input_failed(error);
        }
    }

    fn poll(&mut self, ctx: &egui::Context) {
        // Evaluate freshness and Escape before dispatching any queued events.
        let now = Instant::now();
        if self.armed && (SystemInput::escape() || !self.can_arm(now)) {
            self.disarm();
        }
        if let Err(error) = self.input.release(self.armed.then_some(now)) {
            self.input_failed(error);
        }
        if let Some(error) = self.mic.as_ref().and_then(Microphone::error) {
            self.mic = None;
            self.message = format!("Микрофон отключён · {error}");
        }
        for _ in 0..64 {
            let Some(event) = self
                .stream
                .as_ref()
                .and_then(|stream| stream.events.try_recv().ok())
            else {
                break;
            };
            match event {
                Event::Frame(frame, stamp) => self.receive(frame, stamp, Instant::now()),
                Event::Status(status) => self.status = status,
                Event::Reset(status) => {
                    self.disarm();
                    self.reset();
                    self.status = status;
                }
                Event::End(status) => {
                    self.disarm();
                    self.status = status;
                    self.ended = true;
                    self.finish_record();
                }
            }
        }
        while self
            .received
            .front()
            .is_some_and(|stamp| now.saturating_duration_since(*stamp) > Duration::from_secs(1))
        {
            self.received.pop_front();
        }
        ctx.request_repaint_after(Duration::from_millis(if self.armed { 10 } else { 250 }));
    }
}

impl eframe::App for AirGlove {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll(ctx);
        view::show(self, ctx);
    }
}

impl Drop for AirGlove {
    fn drop(&mut self) {
        self.disarm();
        self.finish_record();
    }
}
