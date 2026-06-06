#!/usr/bin/env python3
"""SOULSENSE entry point.

Usage:
  python soulsense.py                        # live serial, auto-detect port
  python soulsense.py --port /dev/tty.usbXX  # live serial, explicit port
  python soulsense.py --replay captures/example_csi.csv  # file replay
  python soulsense.py --web-port 8080        # change HTTP port (default 8765)
"""
import argparse
import glob
import os
import sys

from aiohttp import web

from motion import MotionEngine
from server import SoulsenseServer
from sources import FileSource, SerialSource

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
DEFAULT_BAUD = 115200
DEFAULT_WEB_PORT = 8765


def find_esp32_port() -> str:
    candidates = (
        glob.glob("/dev/tty.usbserial-*")
        + glob.glob("/dev/tty.wchusbserial*")
        + glob.glob("/dev/tty.SLAB_*")
        + glob.glob("/dev/tty.usbmodem*")
    )
    if not candidates:
        print("[soulsense] No ESP32 serial port found. Connect the board or use --port.")
        sys.exit(1)
    if len(candidates) > 1:
        print(f"[soulsense] Multiple ports found: {candidates}")
        print(f"[soulsense] Using {candidates[0]} — pass --port to choose.")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="SOULSENSE — ESP32 CSI motion visualiser")
    parser.add_argument("--port", help="Serial port (e.g. /dev/tty.usbserial-0001)")
    parser.add_argument("--replay", help="Replay a capture CSV/txt file instead of live serial")
    parser.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT, dest="web_port")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--window", type=int, default=15, help="Motion window size")
    parser.add_argument("--smoothing", type=float, default=0.3, help="Smoothing factor 0–0.99")
    args = parser.parse_args()

    engine = MotionEngine(window_size=args.window, smoothing=args.smoothing)

    if args.replay:
        print(f"[soulsense] Replay mode: {args.replay}")
        source = FileSource(args.replay, loop=True, delay=0.05)
    else:
        port = args.port or find_esp32_port()
        print(f"[soulsense] Live mode: {port} @ {args.baud} baud")
        source = SerialSource(port, baud=args.baud)

    srv = SoulsenseServer(source=source, engine=engine, static_dir=STATIC_DIR)
    app = srv.build_app()

    print(f"[soulsense] Open http://localhost:{args.web_port}")
    web.run_app(app, port=args.web_port, print=lambda _: None)


if __name__ == "__main__":
    main()
