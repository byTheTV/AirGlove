#![cfg_attr(
    all(windows, not(debug_assertions), not(test)),
    windows_subsystem = "windows"
)]

mod app;
mod audio;
mod gestures;
mod input;
mod motion;
mod profiles;
mod protocol;
mod simulation;
mod source;
mod view;

use eframe::egui;
use source::Source;
use std::{ffi::OsString, path::PathBuf};

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

fn parse(args: impl IntoIterator<Item = OsString>) -> Result<Source, &'static str> {
    let mut args = args.into_iter();
    let mut source = None;
    let mut port = None;
    let mut address = None;
    while let Some(arg) = args.next() {
        let next = match arg.to_str() {
            Some("--ble") => Source::Bluetooth(String::new()),
            Some("--usb") => Source::Usb(String::new()),
            Some("--replay") => Source::Replay(PathBuf::from(
                args.next().ok_or("Укажите файл после --replay")?,
            )),
            Some("--port") => {
                if port.is_some() {
                    return Err("Укажите один USB-порт");
                }
                port = Some(
                    args.next()
                        .and_then(|value| value.into_string().ok())
                        .filter(|value| !value.is_empty())
                        .ok_or("Укажите USB-порт после --port")?,
                );
                continue;
            }
            Some("--address") => {
                if address.is_some() {
                    return Err("Укажите один Bluetooth-адрес");
                }
                address = Some(
                    args.next()
                        .and_then(|value| value.into_string().ok())
                        .filter(|value| !value.is_empty())
                        .ok_or("Укажите адрес после --address")?,
                );
                continue;
            }
            _ => {
                return Err(
                    "Доступные параметры: --usb [--port COM5], --ble [--address XX:XX:XX:XX:XX:XX], --replay файл",
                );
            }
        };
        if source.replace(next).is_some() {
            return Err("Выберите один режим запуска");
        }
    }
    match (source, port, address) {
        (None, None, None) => Ok(Source::Demo),
        (Some(Source::Usb(_)) | None, port, None) => Ok(Source::Usb(port.unwrap_or_default())),
        (Some(Source::Bluetooth(_)) | None, None, address) => {
            Ok(Source::Bluetooth(address.unwrap_or_default()))
        }
        (Some(source @ Source::Replay(_)), None, None) => Ok(source),
        _ => Err("Параметры --port и --address относятся к USB и Bluetooth соответственно"),
    }
}

fn main() -> std::process::ExitCode {
    let source = match parse(std::env::args_os().skip(1)) {
        Ok(source) => source,
        Err(error) => {
            rfd::MessageDialog::new()
                .set_title("AirGlove")
                .set_description(error)
                .set_level(rfd::MessageLevel::Error)
                .show();
            return std::process::ExitCode::FAILURE;
        }
    };
    let mut viewport = egui::ViewportBuilder::default()
        .with_inner_size([1100., 760.])
        .with_min_inner_size([720., 570.]);
    if let Ok(icon) =
        eframe::icon_data::from_png_bytes(include_bytes!("../tools/release/AirGlove.png"))
    {
        viewport = viewport.with_icon(icon);
    }
    let options = eframe::NativeOptions {
        viewport,
        ..Default::default()
    };
    match eframe::run_native(
        "AirGlove",
        options,
        Box::new(move |cc| {
            view::configure(&cc.egui_ctx);
            Ok(Box::new(app::AirGlove::new(&cc.egui_ctx, source)))
        }),
    ) {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(error) => {
            rfd::MessageDialog::new()
                .set_title("AirGlove")
                .set_description(format!("Не удалось открыть приложение.\n{error}"))
                .set_level(rfd::MessageLevel::Error)
                .show();
            std::process::ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests;
