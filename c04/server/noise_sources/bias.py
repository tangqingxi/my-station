from core.base_noise_source import NoiseSource
from core.registry import register


@register("BiasNoise")
class BiasNoise(NoiseSource):
    def __init__(self, *, offset: float = 0.0):
        self.offset = float(offset)

    def apply(self, value: float) -> float:
        return float(value) + self.offset
