mod hand;

use crate::{
    VERSION,
    app::{AirGlove, Page},
    gestures::GESTURES,
    input::KEY_NAMES,
    motion::Calibration,
    profiles::{Kind, Profile},
    protocol::{BATTERY_LOW, BATTERY_UNKNOWN, CALIBRATING},
    simulation::{KEYS, SECTIONS, Training},
    source::Source,
};
use eframe::egui::{
    self, Color32 as C, FontData, FontDefinitions, FontFamily, Frame, RichText, Stroke, Ui, vec2,
};
use std::time::Instant;

const BACK: C = C::from_rgb(15, 20, 28);
const PANEL: C = C::from_rgb(23, 30, 42);
const RAIL: C = C::from_rgb(19, 25, 35);
const EDGE: C = C::from_rgb(45, 59, 76);
const TEXT: C = C::from_rgb(232, 241, 252);
const MUTED: C = C::from_rgb(159, 178, 200);
const ACCENT: C = C::from_rgb(121, 233, 202);
const WARNING: C = C::from_rgb(255, 195, 115);
const ERROR: C = C::from_rgb(255, 140, 148);

pub fn configure(ctx: &egui::Context) {
    if let Some(windows) = std::env::var_os("WINDIR") {
        let path = std::path::PathBuf::from(windows).join("Fonts/segoeui.ttf");
        if let Ok(data) = std::fs::read(path) {
            let mut fonts = FontDefinitions::default();
            fonts
                .font_data
                .insert("segoe".into(), FontData::from_owned(data).into());
            for family in [FontFamily::Proportional, FontFamily::Monospace] {
                fonts
                    .families
                    .entry(family)
                    .or_default()
                    .push("segoe".into());
            }
            ctx.set_fonts(fonts);
        }
    }
    let mut visuals = egui::Visuals::dark();
    visuals.panel_fill = BACK;
    visuals.window_fill = PANEL;
    visuals.faint_bg_color = RAIL;
    visuals.override_text_color = Some(TEXT);
    visuals.selection.bg_fill = C::from_rgb(34, 91, 82);
    visuals.widgets.inactive.bg_fill = EDGE;
    visuals.widgets.hovered.bg_fill = C::from_rgb(56, 76, 96);
    visuals.widgets.active.bg_fill = C::from_rgb(47, 104, 96);
    ctx.set_visuals(visuals);
    ctx.style_mut(|style| {
        style.spacing.item_spacing = vec2(8., 10.);
        style.spacing.button_padding = vec2(10., 6.);
        style.spacing.interact_size.y = 31.;
    });
}

fn card() -> Frame {
    Frame::new()
        .fill(PANEL)
        .stroke(Stroke::new(1.0_f32, EDGE))
        .corner_radius(10)
        .inner_margin(16)
}

fn heading(ui: &mut Ui, title: &str, detail: &str) {
    ui.label(RichText::new(title).size(28.).strong());
    ui.label(RichText::new(detail).color(MUTED));
    ui.add_space(6.);
}

fn link_button(ui: &mut Ui, selected: bool, label: &str) -> bool {
    ui.add(
        egui::Button::selectable(selected, RichText::new(label).size(15.))
            .min_size(vec2(ui.available_width(), 35.)),
    )
    .clicked()
}

fn primary(ui: &mut Ui, enabled: bool, label: &str) -> bool {
    ui.add_enabled(
        enabled,
        egui::Button::new(RichText::new(label).strong().color(BACK)).fill(ACCENT),
    )
    .clicked()
}

pub fn show(app: &mut AirGlove, ctx: &egui::Context) {
    egui::SidePanel::left("navigation")
        .exact_width(169.)
        .resizable(false)
        .frame(Frame::new().fill(RAIL).inner_margin(16))
        .show(ctx, |ui| {
            ui.add_space(6.);
            ui.label(RichText::new("AirGlove").size(23.).strong().color(ACCENT));
            ui.label(RichText::new("Управление жестами").size(12.).color(MUTED));
            ui.add_space(18.);
            for (page, label) in [
                (Page::Monitor, "Управление"),
                (Page::Profiles, "Профили"),
                (Page::Training, "Тренировка"),
            ] {
                if link_button(ui, app.page == page, label) {
                    app.set_page(page);
                }
            }
            ui.with_layout(egui::Layout::bottom_up(egui::Align::Min), |ui| {
                ui.label(
                    RichText::new(format!("Версия {VERSION}"))
                        .small()
                        .color(MUTED),
                );
                if app.armed() {
                    ui.label(RichText::new("Ввод включён").color(ACCENT).strong());
                }
            });
        });

    egui::TopBottomPanel::bottom("status")
        .frame(Frame::new().fill(RAIL).inner_margin(10))
        .show(ctx, |ui| {
            if let Some(warning) = &app.profiles.warning {
                ui.label(RichText::new(warning).small().color(WARNING));
            }
            if !app.message.is_empty() {
                ui.label(RichText::new(&app.message).small().color(MUTED));
            }
        });
    egui::CentralPanel::default()
        .frame(Frame::new().fill(BACK).inner_margin(20))
        .show(ctx, |ui| {
            egui::ScrollArea::vertical()
                .auto_shrink([false, false])
                .show(ui, |ui| {
                    ui.set_min_width(ui.available_width());
                    match app.page {
                        Page::Monitor => monitor(app, ctx, ui),
                        Page::Profiles => profiles(app, ui),
                        Page::Training => training(app, ctx, ui),
                    }
                });
        });
}

fn monitor(app: &mut AirGlove, ctx: &egui::Context, ui: &mut Ui) {
    heading(
        ui,
        "Управление",
        "Подключение, калибровка и проверка жестов",
    );
    card().show(ui, |ui| {
        ui.set_min_width(ui.available_width());
        ui.horizontal_wrapped(|ui| {
            if ui
                .selectable_label(
                    matches!(app.source, Source::Demo | Source::Practice),
                    "Симулятор",
                )
                .clicked()
            {
                app.select(ctx, Source::Demo);
            }
            if ui
                .selectable_label(matches!(app.source, Source::Bluetooth(_)), "Bluetooth")
                .clicked()
            {
                app.select(ctx, Source::Bluetooth(app.address.trim().into()));
            }
            if ui
                .selectable_label(matches!(app.source, Source::Usb(_)), "USB")
                .clicked()
            {
                app.select(ctx, Source::Usb(app.port.trim().into()));
            }
            if ui
                .selectable_label(matches!(app.source, Source::Replay(_)), "Открыть запись…")
                .clicked()
            {
                app.open_recording(ctx);
            }
        });
        if matches!(app.source, Source::Usb(_) | Source::Bluetooth(_)) {
            ui.horizontal_wrapped(|ui| {
                let usb = matches!(app.source, Source::Usb(_));
                ui.label(if usb {
                    "COM-порт"
                } else {
                    "BLE-адрес"
                });
                if usb {
                    ui.add(
                        egui::TextEdit::singleline(&mut app.port)
                            .desired_width(95.)
                            .hint_text("Авто"),
                    );
                } else {
                    ui.add(
                        egui::TextEdit::singleline(&mut app.address)
                            .desired_width(170.)
                            .hint_text("Любой AirGlove"),
                    );
                }
                if ui.button("Подключить").clicked() {
                    let source = if usb {
                        Source::Usb(app.port.trim().into())
                    } else {
                        Source::Bluetooth(app.address.trim().into())
                    };
                    app.select(ctx, source);
                }
            });
        }
        let status_color = if app.ended {
            WARNING
        } else if app.latest.is_some() && !app.received.is_empty() {
            ACCENT
        } else {
            MUTED
        };
        ui.label(RichText::new(&app.status).color(status_color));
        if matches!(app.source, Source::Demo)
            && let Some(frame) = app.latest
        {
            ui.label(
                RichText::new(SECTIONS[((frame.millis % 25_000) / 2500) as usize])
                    .small()
                    .color(MUTED),
            );
        }
    });

    card().show(ui, |ui| {
        ui.set_min_width(ui.available_width());
        ui.horizontal_wrapped(|ui| {
            let (label, color) = if app
                .latest
                .is_some_and(|frame| frame.flags & CALIBRATING != 0)
            {
                ("Калибровка гироскопов перчатки", WARNING)
            } else {
                match app.motion.calibration {
                    Calibration::Idle => ("Требуется калибровка", MUTED),
                    Calibration::Collecting => ("Держите кисть неподвижно", WARNING),
                    Calibration::Ready => ("Калибровка готова", ACCENT),
                    Calibration::Partial => ("Не все датчики доступны", WARNING),
                    Calibration::Failed => ("Калибровка не удалась", ERROR),
                }
            };
            ui.label(RichText::new(label).color(color).strong());
            if ui.button("Калибровка").clicked() {
                app.calibrate(ctx);
            }
            if ui
                .add_enabled(app.motion.ready(), egui::Button::new("Задать направление"))
                .clicked()
            {
                app.align();
            }
        });
        ui.horizontal_wrapped(|ui| {
            if app.armed() {
                if ui
                    .add(egui::Button::new("Выключить ввод  ·  Esc").fill(C::from_rgb(112, 52, 62)))
                    .clicked()
                {
                    app.toggle_input();
                }
            } else if primary(ui, app.can_arm(Instant::now()), "Включить системный ввод")
            {
                app.toggle_input();
            }
            if ui
                .button(if app.recording.is_some() {
                    "Остановить запись"
                } else {
                    "Записать телеметрию"
                })
                .clicked()
            {
                app.toggle_record();
            }
        });
        ui.horizontal_wrapped(|ui| {
            profile_picker(app, ui, "monitor_profile");
            ui.add(egui::Slider::new(&mut app.sensitivity, 0.25..=3.).text("Чувствительность"));
        });
    });

    ui.columns(2, |columns| {
        card().show(&mut columns[0], |ui| {
            ui.label(RichText::new("Кисть").strong());
            hand::draw(app, ui);
            let valid = app.latest.map(|frame| frame.valid());
            ui.horizontal_wrapped(|ui| {
                for (i, label) in [
                    "Кисть",
                    "Большой",
                    "Указательный",
                    "Средний",
                    "Безымянный",
                    "Мизинец",
                ]
                .into_iter()
                .enumerate()
                {
                    let status = match valid {
                        Some(mask) if mask & (1 << i) != 0 => "на связи",
                        Some(_) => "нет сигнала",
                        None => "ожидание",
                    };
                    ui.label(
                        RichText::new(format!("CH{i}"))
                            .small()
                            .monospace()
                            .color(hand::channel_color(valid, i)),
                    )
                    .on_hover_text(format!("{label} · {status}"));
                }
            });
        });
        card().show(&mut columns[1], |ui| {
            ui.label(RichText::new("Предпросмотр курсора").strong());
            let (bounds, _) = ui.allocate_exact_size(
                vec2(ui.available_width().max(1.), hand::HEIGHT),
                egui::Sense::hover(),
            );
            let painter = ui.painter_at(bounds);
            painter.rect_filled(bounds, 6, BACK);
            for i in 1..8 {
                let x = bounds.left() + bounds.width() * i as f32 / 8.;
                painter.vline(x, bounds.y_range(), Stroke::new(1.0_f32, RAIL));
            }
            for i in 1..4 {
                let y = bounds.top() + bounds.height() * i as f32 / 4.;
                painter.hline(bounds.x_range(), y, Stroke::new(1.0_f32, RAIL));
            }
            let cursor = bounds.lerp_inside(vec2(app.cursor[0], app.cursor[1]));
            painter.circle_stroke(cursor, 10., Stroke::new(1.0_f32, ACCENT));
            painter.circle_filled(cursor, 3., ACCENT);
            ui.label(
                RichText::new(format!("Колесо {:+}", app.wheel))
                    .small()
                    .color(MUTED),
            );
        });
    });

    card().show(ui, |ui| {
        ui.set_min_width(ui.available_width());
        ui.label(RichText::new(&app.last_gesture).strong());
        ui.horizontal_wrapped(|ui| {
            ui.label(format!("{} Гц", app.received.len()));
            ui.label(format!("Пропущено: {}", app.lost));
            if let Some(frame) = app.latest {
                ui.label(format!("Датчики: {}/6", frame.valid().count_ones()));
                if frame.battery_mv != BATTERY_UNKNOWN {
                    ui.label(
                        RichText::new(format!(
                            "Батарея: {:.2} В",
                            f32::from(frame.battery_mv) / 1000.
                        ))
                        .color(if frame.flags & BATTERY_LOW != 0 {
                            WARNING
                        } else {
                            MUTED
                        }),
                    );
                }
            }
        });
        if !app.activities.is_empty() {
            ui.horizontal_wrapped(|ui| {
                for action in app.activities.iter().rev() {
                    ui.label(RichText::new(action).small().color(ACCENT));
                }
            });
        }
    });
}

fn profile_picker(app: &mut AirGlove, ui: &mut Ui, id: &str) {
    ui.label("Профиль");
    let mut selected = app.profiles.current().id.clone();
    egui::ComboBox::from_id_salt(id)
        .selected_text(&app.profiles.current().name)
        .show_ui(ui, |ui| {
            for profile in &app.profiles.data.profiles {
                ui.selectable_value(&mut selected, profile.id.clone(), &profile.name);
            }
        });
    if selected != app.profiles.current().id {
        app.change_profile(&selected, true);
    }
}

fn profiles(app: &mut AirGlove, ui: &mut Ui) {
    heading(ui, "Профили", "Назначьте действия для жестов");
    card().show(ui, |ui| {
        ui.set_min_width(ui.available_width());
        ui.horizontal_wrapped(|ui| {
            let name = &app.edit.name;
            egui::ComboBox::from_id_salt("edit_profile")
                .selected_text(name)
                .show_ui(ui, |ui| {
                    for profile in &app.profiles.data.profiles {
                        if ui
                            .selectable_label(app.edit.id == profile.id, &profile.name)
                            .clicked()
                        {
                            app.edit = profile.clone();
                            app.delete_confirm = false;
                        }
                    }
                });
            if ui.button("Новый").clicked() {
                app.edit = Profile::new("Новый профиль".into());
                app.delete_confirm = false;
            }
            if ui.button("Копировать").clicked() {
                let mut copy = Profile::new(format!("{} · Копия", app.edit.name));
                copy.bindings.clone_from(&app.edit.bindings);
                app.edit = copy;
                app.delete_confirm = false;
            }
        });
        ui.horizontal_wrapped(|ui| {
            ui.label("Название");
            ui.add(egui::TextEdit::singleline(&mut app.edit.name).desired_width(215.));
            if primary(ui, !app.edit.name.trim().is_empty(), "Сохранить") {
                app.edit.name = app.edit.name.trim().to_owned();
                app.message = match app.profiles.save(app.edit.clone()) {
                    Ok(()) => "Профиль сохранён.".into(),
                    Err(error) => format!("Профиль не сохранён · {error}"),
                };
            }
            let exists = app
                .profiles
                .data
                .profiles
                .iter()
                .any(|profile| profile.id == app.edit.id);
            if ui
                .add_enabled(exists, egui::Button::new("Активировать"))
                .clicked()
            {
                app.change_profile(&app.edit.id.clone(), true);
            }
            if ui
                .add_enabled(
                    exists && app.profiles.data.profiles.len() > 1,
                    egui::Button::new("Удалить"),
                )
                .clicked()
            {
                app.delete_confirm = true;
            }
        });
        if app.delete_confirm {
            ui.horizontal_wrapped(|ui| {
                ui.label(RichText::new(format!("Удалить «{}»?", app.edit.name)).color(WARNING));
                if ui.button("Отмена").clicked() {
                    app.delete_confirm = false;
                }
                if ui.button("Удалить профиль").clicked() {
                    app.delete_confirm = false;
                    match app.profiles.delete(&app.edit.id) {
                        Ok(()) => {
                            app.edit = app.profiles.current().clone();
                            app.message = "Профиль удалён.".into();
                        }
                        Err(error) => app.message = format!("Ошибка удаления · {error}"),
                    }
                }
            });
        }
        if ui
            .checkbox(&mut app.mic_enabled, "Подтверждать щелчок микрофоном")
            .changed()
        {
            app.refresh_mic();
        }
        ui.label(
            RichText::new(
                "Микрофон доступен при подключении по USB или Bluetooth. Звук не записывается.",
            )
            .small()
            .color(MUTED),
        );
    });

    card().show(ui, |ui| {
        for (gesture, label) in GESTURES {
            ui.push_id(gesture, |ui| {
                ui.label(RichText::new(label).strong());
                let mut binding = app.edit.binding(gesture);
                ui.horizontal_wrapped(|ui| {
                    egui::ComboBox::from_id_salt("kind")
                        .selected_text(binding.action.label())
                        .show_ui(ui, |ui| {
                            for action in Kind::ALL {
                                if action != Kind::Pointer || gesture == "motion" {
                                    ui.selectable_value(
                                        &mut binding.action,
                                        action,
                                        action.label(),
                                    );
                                }
                            }
                        });
                    if binding.action == Kind::Key {
                        if !KEY_NAMES.contains(&binding.key.as_str()) {
                            binding.key = "Space".into();
                        }
                        egui::ComboBox::from_id_salt("key")
                            .selected_text(&binding.key)
                            .show_ui(ui, |ui| {
                                for key in KEY_NAMES {
                                    ui.selectable_value(&mut binding.key, (*key).into(), *key);
                                }
                            });
                    } else {
                        binding.key.clear();
                    }
                    if ui.button("Проба").clicked() {
                        app.message = format!("{label} → {}", binding.label());
                    }
                });
                if binding.action == Kind::None {
                    app.edit.bindings.remove(gesture);
                } else {
                    app.edit.bindings.insert(gesture.into(), binding);
                }
                ui.separator();
            });
        }
    });
}

fn training(app: &mut AirGlove, ctx: &egui::Context, ui: &mut Ui) {
    heading(
        ui,
        "Тренировка",
        "Последовательность жестов для профиля Dota 2 · Invoker",
    );
    card().show(ui, |ui| {
        ui.set_min_width(ui.available_width());
        ui.horizontal_wrapped(|ui| {
            if primary(ui, true, "Демо прокаста") {
                app.practice(ctx);
            }
            if ui.button("Сбросить счёт").clicked() {
                app.training = Training::default();
            }
            profile_picker(app, ui, "practice_profile");
        });
        ui.horizontal_wrapped(|ui| {
            for (i, key) in KEYS.iter().enumerate() {
                let color = if i < app.training.progress {
                    ACCENT
                } else if i == app.training.progress {
                    TEXT
                } else {
                    MUTED
                };
                ui.label(RichText::new(*key).monospace().size(22.).color(color));
            }
        });
        ui.label(format!(
            "Шаги: {}/{} · Ошибки: {}",
            app.training.progress,
            KEYS.len(),
            app.training.errors
        ));
        if let Some(duration) = app.training.duration {
            ui.label(RichText::new(format!("Готово за {duration:.2} с")).color(ACCENT));
        }
        ui.label(RichText::new(&app.last_gesture).color(MUTED));
    });
    card().show(ui, |ui| {
        ui.set_min_width(ui.available_width());
        ui.label(RichText::new("Проверить жест вручную").strong());
        ui.horizontal_wrapped(|ui| {
            for (index, (_, label)) in GESTURES[..7].iter().enumerate() {
                if ui.button(*label).clicked() {
                    let now = Instant::now();
                    app.dispatch(index, now, now);
                }
            }
        });
    });
}
