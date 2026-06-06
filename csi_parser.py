import math
from typing import Optional, Dict


def parse_csi_line(line: str) -> Optional[Dict]:
    """Parse one ESP32-CSI-Tool CSI_DATA line.

    Returns a dict with mac, rssi, timestamp, amplitudes — or None if the line
    is not a well-formed CSI_DATA record.
    """
    if not line or not line.startswith("CSI_DATA,"):
        return None
    try:
        open_b = line.index("[")
        close_b = line.index("]", open_b)
    except ValueError:
        return None

    head = line[:open_b].split(",")
    # Need at least through the real_timestamp field (index 23).
    if len(head) < 24:
        return None

    try:
        mac = head[2]
        rssi = int(head[3])
        timestamp = float(head[23])
    except (ValueError, IndexError):
        return None

    raw_str = line[open_b + 1:close_b].split()
    try:
        raw = [int(v) for v in raw_str]
    except ValueError:
        return None
    if len(raw) < 2:
        return None

    amplitudes = []
    for k in range(0, len(raw) - 1, 2):
        imag = raw[k]
        real = raw[k + 1]
        amplitudes.append(math.sqrt(imag * imag + real * real))

    return {
        "mac": mac,
        "rssi": rssi,
        "timestamp": timestamp,
        "amplitudes": amplitudes,
    }
