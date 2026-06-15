from core.base_noise_source import NoiseSource
from core.factory import build_noise
from core.registry import register


@register("CompositeNoise")
class CompositeNoise(NoiseSource):
    def __init__(self, *, sources):
        # sources 可以是已建对象，也可以是 {type,params} 配置。
        self._sources = [build_noise(s) for s in sources]

    def apply(self, value: float) -> float:
        v = float(value)
        for src in self._sources:
            v = src.apply(v)
        return v

    def reset(self) -> None:
        for src in self._sources:
            src.reset()
