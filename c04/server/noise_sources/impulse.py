import random

from core.base_noise_source import NoiseSource
from core.registry import register


@register("ImpulseNoise")
class ImpulseNoise(NoiseSource):
    def __init__(self, *, prob: float = 0.02, amplitude: float = 10.0, seed: int | None = None):
        self.prob = float(prob)
        self.amplitude = float(amplitude)
        self._rng = random.Random(seed)

    def apply(self, value: float) -> float:
        if self._rng.random() < self.prob:
            return float(value) + self._rng.choice((-1.0, 1.0)) * self.amplitude
        return float(value)
