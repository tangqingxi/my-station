import random

from core.base_noise_source import NoiseSource
from core.registry import register


@register("GaussianNoise")
class GaussianNoise(NoiseSource):
    def __init__(self, *, std: float = 1.0, seed: int | None = None):
        self.std = float(std)
        self._rng = random.Random(seed)

    def apply(self, value: float) -> float:
        if self.std <= 0.0:
            return float(value)
        return float(value) + self._rng.gauss(0.0, self.std)
