# core/excitation.py · 激励信号族 · 给被控对象一个“已知输入”，驱动它动起来
#
# 用途：
#   - C4 打分：让箱子的真值有结构地动，回传 filtered 才能跟 true 计算跟踪误差。
#   - C5 参数辨识：同一个激励打进加热器，观测温度响应，给后续辨识留数据。

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from core.params_schema import ParamsSchema
from core.registry import register


class BaseExcitation(ABC):
    """激励基类：value(t) 返回 t 秒时刻的输入幅值。"""

    PARAMS_SCHEMA: ClassVar[ParamsSchema] = {}

    @abstractmethod
    def value(self, t: float) -> float:
        ...

    def reset(self) -> None:
        return


@register("SquareWave")
class SquareWave(BaseExcitation):
    """方波：周期 period 秒，前 duty 比例为 high，其余为 low。"""

    PARAMS_SCHEMA: ClassVar[ParamsSchema] = {
        "period": {
            "type": "float", "default": 20.0, "range": [1.0, 600.0],
            "unit": "s", "label": "周期",
        },
        "duty": {
            "type": "float", "default": 0.5, "range": [0.0, 1.0],
            "label": "占空比",
        },
    }

    def __init__(
        self, *, period: float = 20.0, duty: float = 0.5,
        high: float = 1.0, low: float = 0.0,
    ) -> None:
        self.period = float(period)
        self.duty = float(duty)
        self.high = float(high)
        self.low = float(low)

    def value(self, t: float) -> float:
        phase = (float(t) % self.period) / self.period
        return self.high if phase < self.duty else self.low


@register("PRBS")
class PRBS(BaseExcitation):
    """伪随机二进制序列：每 bit_dt 秒翻一个 bit，固定 seed 可复现。"""

    PARAMS_SCHEMA: ClassVar[ParamsSchema] = {
        "bit_dt": {
            "type": "float", "default": 2.0, "range": [0.1, 60.0],
            "unit": "s", "label": "比特宽度",
        },
    }

    def __init__(
        self, *, bit_dt: float = 2.0, seed: int = 1,
        high: float = 1.0, low: float = 0.0, n_bits: int = 5,
    ) -> None:
        self.bit_dt = float(bit_dt)
        self.high = float(high)
        self.low = float(low)
        self._n = int(n_bits)
        self._mask = (1 << self._n) - 1
        self._seed = (int(seed) & self._mask) or 1
        self._state = self._seed
        self._last_k = -1
        self._bit = self._state & 1

    def _next_bit(self) -> int:
        # 5 位 LFSR，抽头 x^5 + x^3 + 1，足够做课堂演示。
        fb = ((self._state >> 4) ^ (self._state >> 2)) & 1
        self._state = ((self._state << 1) | fb) & self._mask
        return self._state & 1

    def value(self, t: float) -> float:
        k = int(float(t) // self.bit_dt)
        while self._last_k < k:
            self._bit = self._next_bit()
            self._last_k += 1
        return self.high if self._bit else self.low

    def reset(self) -> None:
        self._state = self._seed
        self._last_k = -1
        self._bit = self._state & 1
