use base64::{Engine, engine::general_purpose::STANDARD};
use regex::Regex;
use std::io::{self, BufRead, BufReader, Read, Write};
use std::sync::LazyLock;
use uuid::Uuid;

pub const SERVICE: Uuid = Uuid::from_u128(0x8d032000_1a92_4e8d_a5a2_fbeac12bb201);
pub const TELEMETRY: Uuid = Uuid::from_u128(0x8d032001_1a92_4e8d_a5a2_fbeac12bb201);
pub const CHANNELS: usize = 6;
pub const ALL: u8 = 0x3f;
pub const CALIBRATING: u8 = 1;
pub const BATTERY_LOW: u8 = 2;
pub const BATTERY_UNKNOWN: u16 = u16::MAX;
const SIZE: usize = 124;
const CRC: crc::Crc<u16> = crc::Crc::<u16>::new(&crc::CRC_16_IBM_3740);

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Sample {
    pub accel: [i16; 3],
    pub gyro: [i16; 3],
    pub mag: [i16; 3],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Frame {
    pub sequence: u16,
    pub millis: u32,
    pub samples: [Option<Sample>; CHANNELS],
    pub biased: u8,
    pub flags: u8,
    pub battery_mv: u16,
}

impl Frame {
    pub fn valid(self) -> u8 {
        self.samples
            .iter()
            .enumerate()
            .fold(0, |mask, (i, sample)| {
                mask | (u8::from(sample.is_some()) << i)
            })
    }

    pub fn encode(self) -> [u8; SIZE] {
        let mut bytes = [0; SIZE];
        bytes[..4].copy_from_slice(&[b'A', b'G', 1, self.flags]);
        bytes[4..6].copy_from_slice(&self.sequence.to_le_bytes());
        bytes[6..10].copy_from_slice(&self.millis.to_le_bytes());
        bytes[10] = self.valid();
        bytes[11] = self.biased;
        bytes[12..14].copy_from_slice(&self.battery_mv.to_le_bytes());
        for (sample, out) in self
            .samples
            .iter()
            .zip(bytes[14..122].as_chunks_mut::<18>().0)
        {
            if let Some(sample) = sample {
                for (value, word) in sample
                    .accel
                    .into_iter()
                    .chain(sample.gyro)
                    .chain(sample.mag)
                    .zip(out.as_chunks_mut::<2>().0)
                {
                    *word = value.to_le_bytes();
                }
            }
        }
        let checksum = CRC.checksum(&bytes[..122]);
        bytes[122..].copy_from_slice(&checksum.to_le_bytes());
        bytes
    }

    pub fn decode(bytes: &[u8]) -> Option<Self> {
        if bytes.len() != SIZE
            || bytes[..3] != [b'A', b'G', 1]
            || (bytes[10] | bytes[11]) & !ALL != 0
            || CRC.checksum(&bytes[..122]) != u16::from_le_bytes([bytes[122], bytes[123]])
        {
            return None;
        }
        let word = |offset| u16::from_le_bytes([bytes[offset], bytes[offset + 1]]);
        let mut samples = [None; CHANNELS];
        for (i, sample) in samples.iter_mut().enumerate() {
            if bytes[10] & (1 << i) != 0 {
                let read =
                    |offset| std::array::from_fn(|j| word(14 + i * 18 + offset + j * 2) as i16);
                *sample = Some(Sample {
                    accel: read(0),
                    gyro: read(6),
                    mag: read(12),
                });
            }
        }
        Some(Self {
            sequence: word(4),
            millis: u32::from_le_bytes(bytes[6..10].try_into().ok()?),
            samples,
            biased: bytes[11],
            flags: bytes[3],
            battery_mv: word(12),
        })
    }

    pub fn write(self, out: &mut impl Write) -> io::Result<()> {
        writeln!(out, "AG1 {}", STANDARD.encode(self.encode()))
    }
}

#[derive(Default)]
pub struct Fragments {
    sequence: Option<u16>,
    payload: Vec<u8>,
}

impl Fragments {
    pub fn feed(&mut self, packet: &[u8]) -> Option<Frame> {
        if packet.len() <= 4 || packet[0] != 0xaf {
            return None;
        }
        let sequence = u16::from_le_bytes([packet[1], packet[2]]);
        let offset = usize::from(packet[3]);
        if offset == 0 {
            self.sequence = Some(sequence);
            self.payload.clear();
        }
        if self.sequence != Some(sequence) || self.payload.len() != offset {
            return None;
        }
        self.payload.extend_from_slice(&packet[4..]);
        if self.payload.len() < SIZE {
            return None;
        }
        self.sequence = None;
        Frame::decode(&self.payload).filter(|frame| frame.sequence == sequence)
    }
}

static LEGACY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
    r"^CH([0-5])\s+\w+\s+(?:FAIL I2C read|ACC=\((-?\d+),(-?\d+),(-?\d+)\)\s+GYR=\((-?\d+),(-?\d+),(-?\d+)\)\s+MAG=\((-?\d+),(-?\d+),(-?\d+)\))$"
).unwrap()
});
static MONITOR_TIME: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+->\s+").unwrap());

#[derive(Default)]
pub struct Lines {
    sequence: u16,
    stamp: u32,
    last_channel: Option<usize>,
    samples: [Option<Sample>; CHANNELS],
}

impl Lines {
    pub fn feed(&mut self, line: &str, stamp: u32, timed: bool) -> Option<Frame> {
        let line = line.trim().trim_start_matches('\u{feff}');
        if let Some(encoded) = line.strip_prefix("AG1 ") {
            return STANDARD
                .decode(encoded)
                .ok()
                .and_then(|bytes| Frame::decode(&bytes));
        }
        let fields = LEGACY.captures(line)?;
        let channel = fields[1].parse::<usize>().ok()?;
        let sample = if fields.get(2).is_some() {
            let read = |i: usize| {
                Some([
                    fields[i].parse().ok()?,
                    fields[i + 1].parse().ok()?,
                    fields[i + 2].parse().ok()?,
                ])
            };
            Some(Sample {
                accel: read(2)?,
                gyro: read(5)?,
                mag: read(8)?,
            })
        } else {
            None
        };
        let complete = self
            .last_channel
            .is_some_and(|last| channel <= last || timed && stamp.wrapping_sub(self.stamp) >= 120)
            .then(|| self.flush())
            .flatten();
        if self.last_channel.is_none() {
            self.stamp = stamp;
        }
        self.last_channel = Some(channel);
        self.samples[channel] = sample;
        complete
    }

    pub fn flush(&mut self) -> Option<Frame> {
        self.last_channel.take()?;
        let frame = Frame {
            sequence: self.sequence,
            millis: self.stamp,
            samples: std::mem::take(&mut self.samples),
            biased: 0,
            flags: 0,
            battery_mv: BATTERY_UNKNOWN,
        };
        self.sequence = self.sequence.wrapping_add(1);
        Some(frame)
    }
}

const DAY: u32 = 86_400_000;

pub struct Recording<R> {
    input: BufReader<R>,
    encoding: Option<bool>,
    line: Vec<u8>,
    parser: Lines,
    previous_clock: Option<u32>,
    midnight: u32,
}

impl<R: Read> Recording<R> {
    pub fn new(input: R) -> io::Result<Self> {
        let mut input = BufReader::new(input);
        let encoding = match input.fill_buf()? {
            [0xff, 0xfe, ..] => Some(true),
            [0xfe, 0xff, ..] => Some(false),
            _ => None,
        };
        if encoding.is_some() {
            input.consume(2);
        }
        Ok(Self {
            input,
            encoding,
            line: Vec::new(),
            parser: Lines::default(),
            previous_clock: None,
            midnight: 0,
        })
    }

    fn line(&mut self) -> io::Result<Option<String>> {
        self.line.clear();
        if let Some(little) = self.encoding {
            let mut words = Vec::new();
            while !self.input.fill_buf()?.is_empty() {
                let mut bytes = [0; 2];
                self.input.read_exact(&mut bytes)?;
                let word = if little {
                    u16::from_le_bytes(bytes)
                } else {
                    u16::from_be_bytes(bytes)
                };
                if word == 10 {
                    return Ok(Some(String::from_utf16_lossy(&words)));
                }
                if words.len() >= 8192 {
                    return Err(io::Error::new(
                        io::ErrorKind::InvalidData,
                        "Слишком длинная строка записи",
                    ));
                }
                words.push(word);
            }
            return Ok((!words.is_empty()).then(|| String::from_utf16_lossy(&words)));
        }
        if self
            .input
            .by_ref()
            .take(8193)
            .read_until(b'\n', &mut self.line)?
            == 0
        {
            return Ok(None);
        }
        if self.line.len() > 8192 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "Слишком длинная строка записи",
            ));
        }
        Ok(Some(String::from_utf8_lossy(&self.line).into_owned()))
    }

    pub fn next_frame(&mut self) -> io::Result<Option<Frame>> {
        while let Some(line) = self.line()? {
            let clean = line.trim_start_matches('\u{feff}');
            let frame = if let Some(timestamp) = MONITOR_TIME.captures(clean) {
                let value = |i: usize| timestamp[i].parse::<u32>().unwrap_or_default();
                let clock = ((value(1) * 60 + value(2)) * 60 + value(3)) * 1000 + value(4);
                if self
                    .previous_clock
                    .is_some_and(|before| before.saturating_sub(clock) > DAY / 2)
                {
                    self.midnight = self.midnight.wrapping_add(DAY);
                }
                self.previous_clock = Some(clock);
                self.parser.feed(
                    &clean[timestamp.get(0).unwrap().end()..],
                    self.midnight.wrapping_add(clock),
                    true,
                )
            } else {
                let stamp = (u32::from(self.parser.sequence)
                    + u32::from(self.parser.last_channel.is_some()))
                    * 250;
                self.parser.feed(clean, stamp, false)
            };
            if frame.is_some() {
                return Ok(frame);
            }
        }
        Ok(self.parser.flush())
    }
}
