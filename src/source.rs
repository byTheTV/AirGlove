use crate::{
    protocol::{Fragments, Frame, Lines, Recording, SERVICE, TELEMETRY},
    simulation,
};
use btleplug::{
    api::{Central, Manager as _, Peripheral as _, ScanFilter},
    platform::{Adapter, Manager, Peripheral},
};
use futures_util::StreamExt;
use serialport::SerialPortType;
use std::{
    fs::File,
    io::{self, Read},
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Receiver, SyncSender, TrySendError},
    },
    thread,
    time::{Duration, Instant},
};

#[derive(Clone, Debug)]
pub enum Source {
    Demo,
    Practice,
    Replay(PathBuf),
    Usb(String),
    Bluetooth(String),
}

impl Source {
    pub fn live(&self) -> bool {
        matches!(self, Self::Usb(_) | Self::Bluetooth(_))
    }
}

pub enum Event {
    Frame(Frame, Instant),
    Status(String),
    Reset(String),
    End(String),
}

pub struct Stream {
    pub events: Receiver<Event>,
    stop: Arc<AtomicBool>,
}

impl Stream {
    pub fn start(source: Source, ctx: eframe::egui::Context) -> io::Result<Self> {
        let (sender, events) = mpsc::sync_channel(64);
        let stop = Arc::new(AtomicBool::new(false));
        let worker = Worker {
            sender,
            stop: stop.clone(),
            ctx,
        };
        thread::Builder::new()
            .name("airglove-telemetry".into())
            .spawn(move || {
                let result = match source {
                    Source::Demo | Source::Practice => {
                        worker.demo(matches!(source, Source::Practice));
                        Ok(())
                    }
                    Source::Replay(path) => worker.replay(path),
                    Source::Usb(port) => {
                        worker.usb(&port);
                        Ok(())
                    }
                    Source::Bluetooth(address) => worker.bluetooth(&address),
                };
                if let Err(error) = result {
                    worker.emit(Event::End(error.to_string()));
                }
            })?;
        Ok(Self { events, stop })
    }
}

impl Drop for Stream {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
    }
}

struct Worker {
    sender: SyncSender<Event>,
    stop: Arc<AtomicBool>,
    ctx: eframe::egui::Context,
}

impl Worker {
    fn active(&self) -> bool {
        !self.stop.load(Ordering::Relaxed)
    }

    fn emit(&self, mut event: Event) {
        while self.active() {
            match self.sender.try_send(event) {
                Ok(()) => {
                    self.ctx.request_repaint();
                    return;
                }
                Err(TrySendError::Full(Event::Frame(_, _)) | TrySendError::Disconnected(_)) => {
                    return;
                }
                Err(TrySendError::Full(pending)) => {
                    event = pending;
                    thread::sleep(Duration::from_millis(5));
                }
            }
        }
    }

    fn frame(&self, frame: Frame) {
        self.emit(Event::Frame(frame, Instant::now()));
    }

    fn wait(&self, deadline: Instant) -> bool {
        while self.active() {
            let left = deadline.saturating_duration_since(Instant::now());
            if left.is_zero() {
                return true;
            }
            thread::sleep(left.min(Duration::from_millis(25)));
        }
        false
    }

    fn demo(&self, practice: bool) {
        self.emit(Event::Status("Симулятор активен".into()));
        let mut deadline = Instant::now();
        let mut index = 0u32;
        while self.wait(deadline) {
            if practice && index == simulation::PRACTICE_FRAMES {
                self.emit(Event::End("Демо завершено".into()));
                return;
            }
            self.frame(simulation::frame(index, practice));
            index = index.wrapping_add(1);
            deadline += Duration::from_millis(20);
        }
    }

    fn replay(&self, path: PathBuf) -> io::Result<()> {
        self.emit(Event::Status(format!(
            "Повтор · {}",
            path.file_name()
                .unwrap_or(path.as_os_str())
                .to_string_lossy()
        )));
        let mut recording = Recording::new(File::open(path)?)?;
        let mut deadline = Instant::now();
        let mut previous = None;
        while self.active() {
            let Some(frame) = recording.next_frame()? else {
                break;
            };
            if let Some(last) = previous {
                let elapsed = frame.millis.wrapping_sub(last);
                deadline += Duration::from_millis(if (1..=1000).contains(&elapsed) {
                    u64::from(elapsed)
                } else {
                    20
                });
            }
            if !self.wait(deadline) {
                return Ok(());
            }
            self.frame(frame);
            previous = Some(frame.millis);
        }
        self.emit(Event::End(
            if previous.is_some() {
                "Запись закончилась"
            } else {
                "В файле нет кадров AirGlove"
            }
            .into(),
        ));
        Ok(())
    }

    fn usb(&self, name: &str) {
        while self.active() {
            let result = if name.is_empty() {
                find_usb()
            } else {
                Ok(Some(name.to_string()))
            };
            match result {
                Ok(Some(port)) => {
                    self.emit(Event::Status(format!("Открываю {port}…")));
                    match serialport::new(&port, 115_200)
                        .dtr_on_open(true)
                        .timeout(Duration::from_millis(100))
                        .open()
                    {
                        Ok(mut serial) => {
                            self.emit(Event::Reset(format!("{port} открыт · ожидаю телеметрию")));
                            let result = self.read_usb(&mut serial);
                            if let Err(error) = result {
                                self.emit(Event::Reset(format!("USB · {error}")));
                            }
                        }
                        Err(error) => self.emit(Event::Reset(format!("USB · {error}"))),
                    }
                }
                Ok(None) => self.emit(Event::Status("Ищу USB-порт ESP32-C3…".into())),
                Err(error) => self.emit(Event::Reset(format!("USB · {error}"))),
            }
            self.wait(Instant::now() + Duration::from_millis(1500));
        }
    }

    fn read_usb(&self, port: &mut impl Read) -> io::Result<()> {
        let mut lines = Lines::default();
        let mut pending = Vec::new();
        let mut discarding = false;
        let mut buffer = [0; 512];
        let start = Instant::now();
        let mut last_frame = start;
        while self.active() {
            let mut frame = None;
            match port.read(&mut buffer) {
                Ok(0) => {
                    return Err(io::Error::new(
                        io::ErrorKind::UnexpectedEof,
                        "Соединение закрыто",
                    ));
                }
                Ok(size) => {
                    for &byte in &buffer[..size] {
                        if byte == b'\n' {
                            if !discarding
                                && let Ok(line) = std::str::from_utf8(&pending)
                                && let Some(value) =
                                    lines.feed(line, start.elapsed().as_millis() as u32, false)
                            {
                                frame = Some(value);
                                self.frame(value);
                            }
                            pending.clear();
                            discarding = false;
                        } else if pending.len() == 1024 {
                            discarding = true;
                        } else if !discarding {
                            pending.push(byte);
                        }
                    }
                }
                Err(error)
                    if matches!(
                        error.kind(),
                        io::ErrorKind::TimedOut | io::ErrorKind::WouldBlock
                    ) =>
                {
                    if pending.is_empty() {
                        frame = lines.flush();
                        if let Some(frame) = frame {
                            self.frame(frame);
                        }
                    }
                }
                Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
                Err(error) => return Err(error),
            }
            if frame.is_some() {
                last_frame = Instant::now();
            }
            if last_frame.elapsed() > Duration::from_secs(3) {
                return Err(io::Error::new(
                    io::ErrorKind::TimedOut,
                    "Телеметрия не поступает · повторяю подключение",
                ));
            }
        }
        Ok(())
    }

    fn bluetooth(&self, address: &str) -> io::Result<()> {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_time()
            .build()?;
        runtime.block_on(async {
            while self.active() {
                self.emit(Event::Status("Ищу AirGlove по Bluetooth…".into()));
                match self.discover(address).await {
                    Ok(Some((_adapter, peripheral))) => {
                        let result = self.listen(&peripheral).await;
                        let _ =
                            tokio::time::timeout(Duration::from_secs(2), peripheral.disconnect())
                                .await;
                        let message = result.err().map_or_else(
                            || "Поток прервался · повторяю подключение".into(),
                            |error| error.to_string(),
                        );
                        self.emit(Event::Reset(format!("Bluetooth · {message}")));
                    }
                    Ok(None) => self.emit(Event::Status(
                        "AirGlove пока не найдена · повторяю поиск".into(),
                    )),
                    Err(error) => self.emit(Event::Reset(format!("Bluetooth · {error}"))),
                }
                for _ in 0..15 {
                    if !self.active() {
                        break;
                    }
                    tokio::time::sleep(Duration::from_millis(100)).await;
                }
            }
        });
        Ok(())
    }

    async fn discover(
        &self,
        address: &str,
    ) -> Result<Option<(Adapter, Peripheral)>, Box<dyn std::error::Error>> {
        let manager = Manager::new().await?;
        let Some(adapter) = manager.adapters().await?.into_iter().next() else {
            return Err("Адаптер Bluetooth недоступен".into());
        };
        adapter
            .start_scan(ScanFilter {
                services: vec![SERVICE],
            })
            .await?;
        let result = async {
            for _ in 0..20 {
                if !self.active() {
                    break;
                }
                for device in adapter.peripherals().await? {
                    if !address.is_empty()
                        && !device.address().to_string().eq_ignore_ascii_case(address)
                    {
                        continue;
                    }
                    if device
                        .properties()
                        .await?
                        .is_some_and(|properties| properties.services.contains(&SERVICE))
                    {
                        return Ok(Some(device));
                    }
                }
                tokio::time::sleep(Duration::from_millis(250)).await;
            }
            Ok(None)
        }
        .await;
        let _ = adapter.stop_scan().await;
        // The Windows peripheral holds a weak reference to its adapter.
        result.map(|device| device.map(|device| (adapter, device)))
    }

    async fn listen(&self, device: &Peripheral) -> Result<(), Box<dyn std::error::Error>> {
        self.emit(Event::Status(format!(
            "Подключаюсь к {}…",
            device.address()
        )));
        tokio::time::timeout(Duration::from_secs(12), async {
            device.connect().await?;
            device.discover_services().await
        })
        .await??;
        if !self.active() {
            return Ok(());
        }
        let characteristic = device
            .characteristics()
            .into_iter()
            .find(|characteristic| {
                characteristic.uuid == TELEMETRY && characteristic.service_uuid == SERVICE
            })
            .ok_or("Характеристика телеметрии отсутствует")?;
        let mut notifications = device.notifications().await?;
        tokio::time::timeout(Duration::from_secs(5), device.subscribe(&characteristic)).await??;
        self.emit(Event::Reset("BLE подключён · ожидаю телеметрию".into()));
        let mut fragments = Fragments::default();
        let mut last_frame = Instant::now();
        while self.active() && last_frame.elapsed() < Duration::from_secs(3) {
            match tokio::time::timeout(Duration::from_millis(100), notifications.next()).await {
                Ok(Some(packet)) if packet.uuid == TELEMETRY => {
                    if let Some(frame) = fragments.feed(&packet.value) {
                        last_frame = Instant::now();
                        self.frame(frame);
                    }
                }
                Ok(None) => break,
                _ => {}
            }
        }
        Ok(())
    }
}

fn find_usb() -> serialport::Result<Option<String>> {
    Ok(serialport::available_ports()?.into_iter().find(|port| {
        matches!(&port.port_type, SerialPortType::UsbPort(usb) if (usb.vid, usb.pid) == (0x303a, 0x1001))
    }).map(|port| port.port_name))
}
