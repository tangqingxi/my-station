from __future__ import annotations

from collections import deque
from typing import ClassVar

import numpy as np

from core.base_signal_processor import BaseSignalProcessor
from core.params_schema import ParamsSchema
from core.registry import register


@register("MedianFilter")
class MedianFilter(BaseSignalProcessor):
    PARAMS_SCHEMA: ClassVar[ParamsSchema] = {
        "window_size": {
            "type": "int", "default": 5, "range": [1, 51],
            "step": 1, "label": "中位数窗口",
        },
    }

    def __init__(self, *, window_size: int = 5) -> None:
        self.window_size = int(window_size)
        self._buf: deque = deque(maxlen=self.window_size)

    def process(self, raw: float, dt: float) -> float:
        if self._buf.maxlen != self.window_size:
            self._buf = deque(list(self._buf)[-self.window_size:], maxlen=self.window_size)
        self._buf.append(float(raw))
        return float(np.median(self._buf))

    def reset(self) -> None:
        self._buf.clear()
