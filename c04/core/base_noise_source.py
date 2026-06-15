# core/base_noise_source.py · 噪声 = 可插拔策略对象
from abc import ABC, abstractmethod

from core.registry import register


class NoiseSource(ABC):
    """噪声策略基类：把一个干净测量值变成带噪值。"""

    @abstractmethod
    def apply(self, value: float) -> float:
        """对一个测量值施加扰动，返回带噪值。"""

    def reset(self) -> None:
        """清理内部状态，默认无状态。"""


@register("NullNoise")
class NullNoise(NoiseSource):
    """空噪声：直接返回原值。"""

    def apply(self, value: float) -> float:
        return float(value)
