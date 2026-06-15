from __future__ import annotations

import math
from typing import ClassVar

from core.base_signal_processor import BaseSignalProcessor
from core.params_schema import ParamsSchema
from core.registry import register


@register("LowPassFilter")
class LowPassFilter(BaseSignalProcessor):
    PARAMS_SCHEMA: ClassVar[ParamsSchema] = {
        "cutoff_hz": {
            "type": "float", "default": 2.0, "range": [0.01, 100.0],
            "step": 0.1, "label": "截止频率", "unit": "Hz",
        },
    }

    def __init__(self, *, cutoff_hz: float = 2.0) -> None:
        self.cutoff_hz = float(cutoff_hz)
        self._y_prev: float | None = None

    def process(self, raw: float, dt: float) -> float:
        if dt <= 0.0:
            return float(raw) if self._y_prev is None else self._y_prev
        rc = 1.0 / (2.0 * math.pi * self.cutoff_hz)
        alpha = dt / (rc + dt)
        y = float(raw) if self._y_prev is None else alpha * float(raw) + (1 - alpha) * self._y_prev
        self._y_prev = y
        return y

    def reset(self) -> None:
        self._y_prev = None
