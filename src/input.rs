use crate::motion::Action;
use std::{
    collections::BTreeMap,
    io,
    time::{Duration, Instant},
};
use windows_sys::Win32::UI::Input::KeyboardAndMouse::*;

pub const KEY_NAMES: &[&str] = &[
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "0",
    "Q",
    "W",
    "E",
    "R",
    "T",
    "Y",
    "U",
    "I",
    "O",
    "P",
    "A",
    "S",
    "D",
    "F",
    "G",
    "H",
    "J",
    "K",
    "L",
    "Z",
    "X",
    "C",
    "V",
    "B",
    "N",
    "M",
    "Space",
    "Enter",
    "Tab",
    "Backspace",
    "Left",
    "Right",
    "Up",
    "Down",
    "Insert",
    "Delete",
    "Home",
    "End",
    "Page Up",
    "Page Down",
    "Ctrl",
    "Shift",
    "Alt",
    "-",
    "=",
    "[",
    "]",
    "\\",
    ";",
    "'",
    ",",
    ".",
    "/",
    "`",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
    "F10",
    "F11",
    "F12",
];

fn scan(key: &str) -> Option<u16> {
    for (base, row) in [
        (0x02, "1234567890"),
        (0x10, "QWERTYUIOP"),
        (0x1e, "ASDFGHJKL"),
        (0x2c, "ZXCVBNM"),
    ] {
        if key.len() == 1
            && let Some(index) = row.find(key)
        {
            return Some(base + index as u16);
        }
    }
    Some(match key {
        "Space" => 0x39,
        "Enter" => 0x1c,
        "Tab" => 0x0f,
        "Backspace" => 0x0e,
        "Left" => 0xe04b,
        "Right" => 0xe04d,
        "Up" => 0xe048,
        "Down" => 0xe050,
        "Insert" => 0xe052,
        "Delete" => 0xe053,
        "Home" => 0xe047,
        "End" => 0xe04f,
        "Page Up" => 0xe049,
        "Page Down" => 0xe051,
        "Ctrl" => 0x1d,
        "Shift" => 0x2a,
        "Alt" => 0x38,
        "-" => 0x0c,
        "=" => 0x0d,
        "[" => 0x1a,
        "]" => 0x1b,
        "\\" => 0x2b,
        ";" => 0x27,
        "'" => 0x28,
        "," => 0x33,
        "." => 0x34,
        "/" => 0x35,
        "`" => 0x29,
        "F11" => 0x57,
        "F12" => 0x58,
        _ => {
            let number = key.strip_prefix('F')?.parse::<u16>().ok()?;
            if !(1..=10).contains(&number) {
                return None;
            }
            0x3a + number
        }
    })
}

fn send(events: &[INPUT]) -> usize {
    // Each event has the Windows INPUT layout and stays alive through SendInput.
    unsafe {
        SendInput(
            events.len() as u32,
            events.as_ptr(),
            size_of::<INPUT>() as i32,
        ) as usize
    }
}

fn rejected() -> io::Error {
    io::Error::other("Windows отклонила системный ввод")
}

fn mouse(dx: i32, dy: i32, data: i32, flags: MOUSE_EVENT_FLAGS) -> INPUT {
    INPUT {
        r#type: INPUT_MOUSE,
        Anonymous: INPUT_0 {
            mi: MOUSEINPUT {
                dx,
                dy,
                mouseData: data as u32,
                dwFlags: flags,
                time: 0,
                dwExtraInfo: 0,
            },
        },
    }
}

fn keyboard(scan: u16, up: bool) -> io::Result<()> {
    let mut flags = KEYEVENTF_SCANCODE;
    if up {
        flags |= KEYEVENTF_KEYUP;
    }
    if scan > 255 {
        flags |= KEYEVENTF_EXTENDEDKEY;
    }
    let event = INPUT {
        r#type: INPUT_KEYBOARD,
        Anonymous: INPUT_0 {
            ki: KEYBDINPUT {
                wVk: 0,
                wScan: scan & 0xff,
                dwFlags: flags,
                time: 0,
                dwExtraInfo: 0,
            },
        },
    };
    if send(&[event]) == 1 {
        Ok(())
    } else {
        Err(rejected())
    }
}

#[derive(Default)]
pub struct SystemInput {
    x: f64,
    y: f64,
    held: BTreeMap<u16, Instant>,
    pending_button_up: Option<MOUSE_EVENT_FLAGS>,
}

impl SystemInput {
    pub fn escape() -> bool {
        // GetAsyncKeyState's sign bit indicates whether the global key is held.
        unsafe { GetAsyncKeyState(i32::from(VK_ESCAPE)) < 0 }
    }

    pub fn apply(&mut self, action: Action) -> io::Result<()> {
        self.x += action.dx;
        self.y += action.dy;
        let (dx, dy) = (self.x as i32, self.y as i32);
        self.x -= f64::from(dx);
        self.y -= f64::from(dy);
        if (dx != 0 || dy != 0) && send(&[mouse(dx, dy, 0, MOUSEEVENTF_MOVE)]) != 1 {
            return Err(rejected());
        }
        if action.wheel != 0 && send(&[mouse(0, 0, action.wheel * 120, MOUSEEVENTF_WHEEL)]) != 1 {
            return Err(rejected());
        }
        if let Some(right) = action.click {
            let (down, up) = if right {
                (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP)
            } else {
                (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP)
            };
            match send(&[mouse(0, 0, 0, down), mouse(0, 0, 0, up)]) {
                2 => {}
                1 => {
                    self.pending_button_up = Some(up);
                    self.release(None)?;
                    return Err(rejected());
                }
                _ => return Err(rejected()),
            }
        }
        Ok(())
    }

    pub fn tap(&mut self, key: &str, now: Instant) -> io::Result<()> {
        let code = scan(key).ok_or_else(|| io::Error::other("Неизвестная клавиша"))?;
        if self.held.contains_key(&code) {
            keyboard(code, true)?;
            self.held.remove(&code);
        }
        keyboard(code, false)?;
        self.held.insert(code, now + Duration::from_millis(45));
        Ok(())
    }

    pub fn release(&mut self, now: Option<Instant>) -> io::Result<()> {
        let mut failed = false;
        self.held.retain(|&code, deadline| {
            if now.is_some_and(|time| time < *deadline) {
                return true;
            }
            let error = keyboard(code, true).is_err();
            failed |= error;
            error
        });
        if let Some(flags) = self.pending_button_up {
            if send(&[mouse(0, 0, 0, flags)]) == 1 {
                self.pending_button_up = None;
            } else {
                failed = true;
            }
        }
        if now.is_none() {
            self.x = 0.;
            self.y = 0.;
        }
        if failed { Err(rejected()) } else { Ok(()) }
    }
}

impl Drop for SystemInput {
    fn drop(&mut self) {
        let _ = self.release(None);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn supported_keys_have_distinct_codes() {
        let codes: std::collections::BTreeSet<_> =
            KEY_NAMES.iter().map(|name| scan(name).unwrap()).collect();
        assert_eq!(codes.len(), KEY_NAMES.len());
        assert_eq!(scan("Left"), Some(0xe04b));
    }
}
