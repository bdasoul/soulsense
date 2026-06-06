from collections import deque
from statistics import pstdev
from typing import Dict, List, Optional


class MotionEngine:
    PEAK_DECAY = 0.999

    def __init__(self, window_size: int = 15, smoothing: float = 0.3):
        self.window_size = window_size
        self.smoothing = smoothing
        self._window = deque(maxlen=window_size)
        self._peak = 0.0
        self._smoothed = 0.0
        self._energy_peak = 0.0
        self._vel_peak = 0.0
        self._prev_raw = 0.0

    def set_params(self, window_size: Optional[int] = None,
                   smoothing: Optional[float] = None) -> None:
        if window_size is not None and window_size >= 2:
            self.window_size = window_size
            self._window = deque(self._window, maxlen=window_size)
        if smoothing is not None:
            self.smoothing = max(0.0, min(0.99, smoothing))

    def update(self, amplitudes: List[float]) -> Dict[str, float]:
        self._window.append(list(amplitudes))

        if len(self._window) < 2:
            return {"motion_raw": 0.0, "motion": 0.0,
                    "energy": 0.0, "spread": 0.0, "velocity": 0.0}

        n_sub = min(len(a) for a in self._window)
        stds = [pstdev([a[k] for a in self._window]) for k in range(n_sub)]

        # Motion — mean per-subcarrier stddev, normalized + smoothed
        raw = sum(stds) / n_sub if n_sub else 0.0
        self._peak = max(self._peak * self.PEAK_DECAY, raw)
        normalized = max(0.0, min(1.0, raw / self._peak if self._peak > 0 else 0.0))
        self._smoothed = self.smoothing * self._smoothed + (1.0 - self.smoothing) * normalized

        # Energy — mean amplitude of the most recent packet, normalized
        current = self._window[-1]
        energy_raw = sum(current) / len(current) if current else 0.0
        self._energy_peak = max(self._energy_peak * self.PEAK_DECAY, energy_raw)
        energy = max(0.0, min(1.0, energy_raw / self._energy_peak if self._energy_peak > 0 else 0.0))

        # Spread — fraction of subcarriers with above-mean stddev
        if n_sub > 0:
            mean_std = raw
            spread = sum(1 for s in stds if s > mean_std * 0.5) / n_sub
        else:
            spread = 0.0

        # Velocity — rate of change of raw motion, normalized
        velocity_raw = abs(raw - self._prev_raw)
        self._vel_peak = max(self._vel_peak * self.PEAK_DECAY, velocity_raw)
        velocity = max(0.0, min(1.0, velocity_raw / self._vel_peak if self._vel_peak > 0 else 0.0))
        self._prev_raw = raw

        return {
            "motion_raw": raw,
            "motion": self._smoothed,
            "energy": energy,
            "spread": spread,
            "velocity": velocity,
        }
