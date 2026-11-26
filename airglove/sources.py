"""Transport adapters that emit the same frames for every input source."""

import asyncio
import time

from .protocol import Fragments, SERVICE, SerialFrames, TELEMETRY, elapsed_ms, read_recording
from .simulation import PRACTICE_DURATION, RATE, frame_at, practice_frame_at


def demo(emit, stop, practice=False):
    start = time.monotonic()
    index = 0
    emit("status", "Симулятор активен")
    while not stop.wait(max(0, start + index / RATE - time.monotonic())):
        if practice and index >= PRACTICE_DURATION * RATE:
            emit("ended", "Демо прокаста завершено")
            return
        emit("frame", practice_frame_at(index) if practice else frame_at(index))
        index += 1


def replay(emit, stop, path):
    previous = None
    target = time.monotonic()
    emit("status", f"Повтор · {path.name}")
    for frame in read_recording(path):
        if previous is not None:
            delay = elapsed_ms(frame.millis, previous)
            target += (delay if 0 < delay <= 1000 else 20) / 1000
        if stop.wait(max(0, target - time.monotonic())):
            return
        emit("frame", frame)
        previous = frame.millis
    emit("ended", "Запись закончилась" if previous is not None else "В файле нет кадров AirGlove")


def usb(emit, stop, port_name):
    import serial
    from serial.tools import list_ports

    while not stop.is_set():
        try:
            target = port_name or next((p.device for p in list_ports.comports()
                                        if (p.vid, p.pid) == (0x303A, 0x1001)), None)
            if target is None:
                emit("status", "Ищу USB-порт ESP32-C3…")
            else:
                emit("status", f"Открываю {target}…")
                with serial.Serial(target, 115200, timeout=0.1) as port:
                    emit("reset", f"{target} открыт · ожидаю телеметрию")
                    _read_usb(emit, stop, port)
        except (serial.SerialException, OSError) as exc:
            emit("reset", f"USB · {exc}")
        if stop.wait(1.5):
            return


def _read_usb(emit, stop, port):
    parser = SerialFrames()
    pending = bytearray()
    discarding = False
    while not stop.is_set():
        chunk = port.read_until(size=512)
        if not chunk:
            frame = parser.flush()
        else:
            pending.extend(chunk)
            discarding = discarding or len(pending) > 1024
            if not chunk.endswith(b"\n"):
                if discarding:
                    pending.clear()
                continue
            frame = None if discarding else parser.feed(pending.decode("ascii", errors="replace"))
            pending.clear()
            discarding = False
        if frame is not None:
            emit("frame", frame)


async def _bluetooth(emit, address):
    from bleak import BleakClient, BleakScanner

    def matches(device, advertisement):
        if address and device.address.casefold() != address.casefold():
            return False
        return SERVICE in advertisement.service_uuids

    while True:
        emit("status", "Ищу AirGlove по Bluetooth…")
        try:
            device = await BleakScanner.find_device_by_filter(matches, timeout=5)
            if device is None:
                emit("status", "AirGlove пока не найдена · повторяю поиск")
            else:
                await _listen_ble(BleakClient, device, emit)
        except Exception as exc:
            emit("reset", f"Bluetooth · {exc}")
        await asyncio.sleep(1.5)


async def _listen_ble(client_type, device, emit):
    lost = asyncio.Event()
    fragments = Fragments()
    last_frame = time.monotonic()

    def notification(_sender, packet):
        nonlocal last_frame
        frame = fragments.feed(packet)
        if frame is not None:
            last_frame = time.monotonic()
            emit("frame", frame)

    emit("status", f"Подключаюсь к {device.name or device.address}…")
    async with client_type(device, disconnected_callback=lambda _client: lost.set(), timeout=12) as client:
        emit("reset", "BLE подключён · ожидаю телеметрию")
        await asyncio.wait_for(client.start_notify(TELEMETRY, notification), timeout=5)
        last_frame = time.monotonic()
        while client.is_connected and not lost.is_set():
            await asyncio.sleep(0.20)
            if time.monotonic() - last_frame > 3:
                break
    emit("reset", "Поток BLE прервался · повторяю подключение")


def bluetooth(emit, stop, address):
    async def run():
        task = asyncio.create_task(_bluetooth(emit, address))
        try:
            while not stop.is_set() and not task.done():
                await asyncio.sleep(0.1)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    asyncio.run(run())
