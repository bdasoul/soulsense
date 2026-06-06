from __future__ import annotations
import time
from typing import TYPE_CHECKING, Iterator, Dict
from csi_parser import parse_csi_line
if TYPE_CHECKING:
    from motion import MotionEngine


class FileSource:
    """Replays CSI_DATA lines from a capture file. Used for tests, hardware-free
    development, and (later) Phase C analysis."""

    def __init__(self, path: str, loop: bool = False, delay: float = 0.01):
        self.path = path
        self.loop = loop
        self.delay = delay
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def lines(self) -> Iterator[str]:
        while not self._stop:
            with open(self.path, "r") as f:
                for line in f:
                    if self._stop:
                        return
                    line = line.strip()
                    if line:
                        if self.delay:
                            time.sleep(self.delay)
                        yield line
            if not self.loop:
                return


class SerialSource:
    """Reads CSI_DATA lines from the live ESP32 AP serial port. Resilient to the
    port disappearing or being busy: retries every 2s and reports status via the
    on_status callback (called with True=connected, False=disconnected)."""

    def __init__(self, port: str, baud: int = 115200, on_status=None):
        self.port = port
        self.baud = baud
        self.on_status = on_status or (lambda connected: None)
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def lines(self) -> Iterator[str]:
        import serial  # pyserial; imported lazily so tests don't need hardware
        while not self._stop:
            try:
                ser = serial.Serial(self.port, self.baud, timeout=1)
                self.on_status(True)
            except (OSError, serial.SerialException) as e:
                self.on_status(False)
                print(f"[soulsense] cannot open {self.port} ({e}); "
                      f"is an idf.py monitor still open? retrying in 2s…")
                time.sleep(2)
                continue
            try:
                while not self._stop:
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        yield line
            except (OSError, serial.SerialException):
                self.on_status(False)
                try:
                    ser.close()
                except Exception:
                    pass
                time.sleep(2)
        # Clean stop — notify caller the source is no longer connected.
        self.on_status(False)


def run_pipeline(source, engine: MotionEngine) -> Iterator[Dict]:
    """Drive a source through the parser + motion engine, yielding one JSON-ready
    message per valid CSI packet."""
    for line in source.lines():
        rec = parse_csi_line(line)
        if rec is None:
            continue
        m = engine.update(rec["amplitudes"])
        yield {
            "t": rec["timestamp"],
            "motion": m["motion"],
            "motion_raw": m["motion_raw"],
            "rssi": rec["rssi"],
            "amplitudes": rec["amplitudes"],
        }
