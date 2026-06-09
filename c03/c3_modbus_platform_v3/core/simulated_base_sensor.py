# core/simulated_base_sensor.py · 服务端「仿真测量」基类 · 加噪是参数 noise_std,不是子类
import random
from abc import ABC, abstractmethod
from .base_plant import BasePlant


class SimulatedBaseSensor(ABC):
    def __init__(self, name: str, *, noise_std: float = 0.0, seed: int | None = None):
        self.name = name
        self._noise_std = float(noise_std)
        self._rng = random.Random(seed) if seed is not None else random

    @abstractmethod
    def read(self, plant: BasePlant) -> float: ...

    def _add_noise(self, v: float) -> float:
        if self._noise_std > 0.0:
            v = v + self._rng.gauss(0.0, self._noise_std)
        return float(v)