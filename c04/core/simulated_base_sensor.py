# core/simulated_base_sensor.py · 服务端「仿真测量」基类 · 加噪委托给 NoiseSource 策略
from abc import ABC, abstractmethod

from .base_plant import BasePlant
from .factory import build_noise


class SimulatedBaseSensor(ABC):
    def __init__(self, name: str, *, noise=None):
        self.name = name
        self._noise = build_noise(noise)

    @abstractmethod
    def read(self, plant: BasePlant) -> float: ...

    def _add_noise(self, v: float) -> float:
        return float(self._noise.apply(float(v)))
