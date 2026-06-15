from __future__ import annotations

from typing import ClassVar

from core.base_signal_processor import BaseSignalProcessor
from core.params_schema import ParamsSchema
from core.registry import register


@register("MyFilter")
class MyFilter(BaseSignalProcessor):
    """示例：一阶指数加权移动平均，y = alpha*x + (1-alpha)*y_prev。"""

    PARAMS_SCHEMA: ClassVar[ParamsSchema] = {
        "alpha": {
            "type": "float", "default": 0.2, "range": [0.0, 1.0],
            "step": 0.01, "label": "平滑系数 alpha",
        },
    }

    def __init__(self, *, alpha: float = 0.2) -> None:
        self.alpha = float(alpha)
        self._y_prev: float | None = None

    def process(self, raw: float, dt: float) -> float:
        x = float(raw)
        self._y_prev = x if self._y_prev is None else self.alpha * x + (1 - self.alpha) * self._y_prev
        return self._y_prev

    def reset(self) -> None:
        self._y_prev = None
