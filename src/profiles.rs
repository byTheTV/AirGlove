use crate::{gestures::GESTURES, input::KEY_NAMES};
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, HashSet},
    fs,
    io::{self, Write},
    path::PathBuf,
};
use tempfile::Builder;
use uuid::Uuid;

#[derive(Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Kind {
    #[default]
    None,
    Key,
    Left,
    Right,
    Up,
    Down,
    Next,
    Pointer,
}

impl Kind {
    pub const ALL: [Self; 8] = [
        Self::None,
        Self::Key,
        Self::Left,
        Self::Right,
        Self::Up,
        Self::Down,
        Self::Next,
        Self::Pointer,
    ];
    pub fn label(self) -> &'static str {
        match self {
            Self::None => "Без действия",
            Self::Key => "Клавиша",
            Self::Left => "Левый клик",
            Self::Right => "Правый клик",
            Self::Up => "Прокрутка вверх",
            Self::Down => "Прокрутка вниз",
            Self::Next => "Следующий профиль",
            Self::Pointer => "Движение курсора",
        }
    }
}

#[derive(Clone, Default, Serialize, Deserialize)]
pub struct Binding {
    pub action: Kind,
    #[serde(default)]
    pub key: String,
}

impl Binding {
    pub fn label(&self) -> &str {
        if self.action == Kind::Key {
            &self.key
        } else {
            self.action.label()
        }
    }
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Profile {
    pub id: String,
    pub name: String,
    pub bindings: BTreeMap<String, Binding>,
}

impl Profile {
    pub fn binding(&self, gesture: &str) -> Binding {
        self.bindings.get(gesture).cloned().unwrap_or_default()
    }

    pub fn new(name: String) -> Self {
        Self {
            id: Uuid::new_v4().simple().to_string(),
            name,
            bindings: BTreeMap::from([("snap".into(), binding(Kind::Next, ""))]),
        }
    }
}

fn binding(action: Kind, key: &str) -> Binding {
    Binding {
        action,
        key: key.into(),
    }
}

#[derive(Clone, Serialize, Deserialize)]
pub struct ProfileData {
    version: u8,
    pub active: String,
    pub profiles: Vec<Profile>,
}

impl Default for ProfileData {
    fn default() -> Self {
        let desktop = Profile {
            id: "desktop".into(),
            name: "Рабочий стол".into(),
            bindings: BTreeMap::from([
                ("motion".into(), binding(Kind::Pointer, "")),
                ("scroll_up".into(), binding(Kind::Up, "")),
                ("scroll_down".into(), binding(Kind::Down, "")),
                ("thumb_index".into(), binding(Kind::Left, "")),
                ("thumb_middle".into(), binding(Kind::Right, "")),
                ("snap".into(), binding(Kind::Next, "")),
            ]),
        };
        let mut invoker = desktop.clone();
        invoker.id = "invoker".into();
        invoker.name = "Dota 2 · Invoker".into();
        invoker.bindings.remove("scroll_up");
        invoker.bindings.remove("scroll_down");
        for ((gesture, _), key) in GESTURES.iter().zip(["D", "Q", "W", "E", "R", "F"]) {
            invoker
                .bindings
                .insert((*gesture).into(), binding(Kind::Key, key));
        }
        Self {
            version: 1,
            active: desktop.id.clone(),
            profiles: vec![desktop, invoker],
        }
    }
}

impl ProfileData {
    fn validate(&mut self) -> io::Result<()> {
        if self.version != 1 || self.profiles.is_empty() {
            return Err(io::Error::other(
                "Неизвестный формат или пустой список профилей",
            ));
        }
        let mut ids = HashSet::new();
        for profile in &mut self.profiles {
            if profile.name.trim().is_empty()
                || profile.id.is_empty()
                || !ids.insert(profile.id.as_str())
            {
                return Err(io::Error::other("Проверьте имя и идентификатор профиля"));
            }
            profile
                .bindings
                .retain(|key, _| GESTURES.iter().any(|(gesture, _)| key == gesture));
            for (gesture, binding) in &profile.bindings {
                if binding.action == Kind::Pointer && gesture != "motion"
                    || binding.action == Kind::Key && !KEY_NAMES.contains(&binding.key.as_str())
                {
                    return Err(io::Error::other(format!(
                        "Недопустимое назначение жеста {gesture}"
                    )));
                }
            }
        }
        if !ids.contains(self.active.as_str()) {
            self.active = self.profiles[0].id.clone();
        }
        Ok(())
    }
}

pub struct Profiles {
    pub data: ProfileData,
    current: String,
    path: PathBuf,
    pub warning: Option<String>,
    needs_backup: bool,
}

impl Profiles {
    pub fn load() -> Self {
        let directory = if let Some(local) = std::env::var_os("LOCALAPPDATA") {
            PathBuf::from(local)
        } else {
            std::env::temp_dir()
        };
        Self::open(directory.join("AirGlove").join("profiles.json"))
    }

    fn open(path: PathBuf) -> Self {
        let mut data = ProfileData::default();
        let mut warning = None;
        let mut needs_backup = false;
        match fs::read(&path) {
            Ok(raw) => {
                match serde_json::from_slice::<ProfileData>(&raw)
                    .map_err(io::Error::from)
                    .and_then(|mut data| {
                        data.validate()?;
                        Ok(data)
                    }) {
                    Ok(parsed) => data = parsed,
                    Err(error) => {
                        warning = Some(format!("Профили не загружены · {error}"));
                        needs_backup = true;
                    }
                }
            }
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            Err(error) => {
                warning = Some(format!("Профили не прочитаны · {error}"));
                needs_backup = true;
            }
        }
        Self {
            current: data.active.clone(),
            path,
            warning,
            needs_backup,
            data,
        }
    }

    pub fn current(&self) -> &Profile {
        self.data
            .profiles
            .iter()
            .find(|profile| profile.id == self.current)
            .unwrap_or(&self.data.profiles[0])
    }

    pub fn cycle(&mut self) {
        let index = self
            .data
            .profiles
            .iter()
            .position(|profile| profile.id == self.current)
            .unwrap_or(0);
        self.current = self.data.profiles[(index + 1) % self.data.profiles.len()]
            .id
            .clone();
    }

    pub fn activate(&mut self, id: &str) -> io::Result<()> {
        let mut data = self.data.clone();
        data.active = id.into();
        self.commit(data)?;
        self.current.clone_from(&self.data.active);
        Ok(())
    }

    pub fn preview(&mut self, id: &str) {
        if self.data.profiles.iter().any(|profile| profile.id == id) {
            self.current = id.into();
        }
    }

    pub fn save(&mut self, profile: Profile) -> io::Result<()> {
        let mut data = self.data.clone();
        if let Some(existing) = data.profiles.iter_mut().find(|item| item.id == profile.id) {
            *existing = profile;
        } else {
            data.profiles.push(profile);
        }
        self.commit(data)
    }

    pub fn delete(&mut self, id: &str) -> io::Result<()> {
        let mut data = self.data.clone();
        data.profiles.retain(|profile| profile.id != id);
        self.commit(data)?;
        if self.current == id {
            self.current.clone_from(&self.data.active);
        }
        Ok(())
    }

    fn commit(&mut self, mut data: ProfileData) -> io::Result<()> {
        data.validate()?;
        let directory = self
            .path
            .parent()
            .ok_or_else(|| io::Error::other("Нет папки профилей"))?;
        fs::create_dir_all(directory)?;
        if self.needs_backup {
            let mut original = fs::File::open(&self.path)?;
            let mut backup = Builder::new()
                .prefix("profiles-backup-")
                .suffix(".json")
                .tempfile_in(directory)?;
            io::copy(&mut original, &mut backup)?;
            backup.as_file().sync_all()?;
            backup.keep().map_err(|error| error.error)?;
            self.needs_backup = false;
        }
        let mut temporary = Builder::new()
            .prefix("profiles-")
            .suffix(".tmp")
            .tempfile_in(directory)?;
        serde_json::to_writer_pretty(&mut temporary, &data)?;
        temporary.write_all(b"\n")?;
        temporary.as_file().sync_all()?;
        temporary.persist(&self.path).map_err(|error| error.error)?;
        self.data = data;
        self.warning = None;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_one_profiles_round_trip_and_keep_an_active_profile() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("profiles.json");
        let python_layout = br#"{"version":1,"active":"example","profiles":[{"id":"example","name":"Existing","bindings":{"tap_1":{"action":"key","key":"F12"},"motion":{"action":"pointer","key":""}}}]}"#;
        fs::write(&path, python_layout).unwrap();
        let mut book = Profiles::open(path.clone());
        assert_eq!(book.current().binding("tap_1").key, "F12");
        assert!(book.delete("example").is_err());
        assert_eq!(fs::read(&path).unwrap(), python_layout);
        let mut changed = book.current().clone();
        changed.name = "Renamed".into();
        book.save(changed).unwrap();
        assert_eq!(Profiles::open(path).current().name, "Renamed");
    }

    #[test]
    fn malformed_profiles_are_backed_up_before_editing() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("profiles.json");
        let broken = b"{broken";
        fs::write(&path, broken).unwrap();
        let mut book = Profiles::open(path.clone());
        assert!(book.warning.is_some());
        book.activate("invoker").unwrap();
        assert_eq!(Profiles::open(path).current().id, "invoker");
        let saved = fs::read_dir(directory.path())
            .unwrap()
            .filter_map(Result::ok)
            .find(|file| {
                file.file_name()
                    .to_string_lossy()
                    .starts_with("profiles-backup-")
            })
            .unwrap();
        assert_eq!(fs::read(saved.path()).unwrap(), broken);
    }
}
