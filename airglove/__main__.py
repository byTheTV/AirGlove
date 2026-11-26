"""Run AirGlove in simulator, live, or recording playback mode."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--ble", action="store_true", help="connect by Bluetooth")
    source.add_argument("--usb", action="store_true", help="connect by USB")
    source.add_argument("--replay", type=Path, help="play an AG1 recording or AirGloveCheck log")
    parser.add_argument("--port", help="USB serial port, e.g. COM5")
    parser.add_argument("--address", help="restrict Bluetooth discovery to this device address")
    args = parser.parse_args()
    if args.replay and not args.replay.is_file():
        parser.error(f"recording not found: {args.replay}")

    import tkinter as tk
    from .app import Dashboard

    root = tk.Tk()
    app = Dashboard(root, args.port, args.address)
    if args.replay:
        app.select("replay", args.replay)
    elif args.ble:
        app.select("bluetooth")
    elif args.usb or args.port:
        app.select("usb")
    else:
        app.select("demo")
    root.mainloop()


if __name__ == "__main__":
    main()
