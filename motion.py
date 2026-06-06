from collections import deque
from statistics import pstdev
from typing import Dict, List, Optional


class MotionEngine:
    """Turns a stream of CSI amplitude vectors into a normalized motion value.

    motion_raw = mean over subcarriers of the per-subcarrier population stddev
    across the last `window_size` packets. Still channel -> ~0. Movement -> up.
    motion = motion_raw normalized to a rolling peak, clamped 0..1, then
    exponentially smoothed by `smoothing` (0 = no smoothing, ->1 = very smooth).
    """

    PEAK_DECAY = 0.999  # rolling peak slowly relaxes so the scale re-calibrates

    def __init__(self, window_size: int = 15, smoothing: float = 0.3):
        self.window_size = window_size
        self.smoothing = smoothing
        self._window = deque(maxlen=window_size)
        self._peak = 0.0
        self._smoothed = 0.0

    def set_params(self, window_size: Optional[int] = None,
                   smoothing: Optional[float] = None) -> None:
        if window_size is not None and window_size >= 2:
            self.window_size = window_size
            new_window = deque(self._window, maxlen=window_size)
            self._window = new_window
        if smoothing is not None:
            self.smoothing = max(0.0, min(0.99, smoothing))

    def update(self, amplitudes: List[float]) -> Dict[str, float]:
        self._window.append(list(amplitudes))

        if len(self._window) < 2:
            return {"motion_raw": 0.0, "motion": 0.0}

        n_sub = min(len(a) for a in self._window)
        stds = []
        for k in range(n_sub):
            column = [a[k] for a in self._window]
            stds.append(pstdev(column))
        raw = sum(stds) / n_sub if n_sub else 0.0

        self._peak = max(self._peak * self.PEAK_DECAY, raw)
        normalized = (raw / self._peak) if self._peak > 0 else 0.0
        normalized = max(0.0, min(1.0, normalized))

        a = self.smoothing
        self._smoothed = a * self._smoothed + (1.0 - a) * normalized

        return {"motion_raw": raw, "motion": self._smoothed}
