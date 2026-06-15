import math

from core.base_noise_source import NoiseSource
from core.registry import register


@register("SineNoise")
class SineNoise(NoiseSource):
    def __init__(
        self, *, amplitude: float = 1.0, freq_hz: float = 1.0,
        phase: float = 0.0, dt: float = 0.1,
    ):
        self.amplitude = float(amplitude)
        self.freq_hz = float(freq_hz)
        self.phase = float(phase)
        self.dt = float(dt)
        self._n = 0

    def apply(self, value: float) -> float:
        t = self._n * self.dt
        self._n += 1
        return float(value) + self.amplitude * math.sin(
            2.0 * math.pi * self.freq_hz * t + self.phase
        )

    def reset(self) -> None:
        self._n = 0
