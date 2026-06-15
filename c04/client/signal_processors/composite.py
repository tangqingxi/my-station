from __future__ import annotations

from typing import ClassVar

from core.base_signal_processor import BaseSignalProcessor
from core.factory import build
from core.params_schema import ParamsSchema
from core.registry import register


@register("CompositeProcessor")
class CompositeProcessor(BaseSignalProcessor):
    """多个处理器串联：上一级输出作为下一级输入。"""

    PARAMS_SCHEMA: ClassVar[ParamsSchema] = {}

    def __init__(self, *, steps):
        self._steps = [s if isinstance(s, BaseSignalProcessor) else build(s) for s in steps]

    def process(self, raw: float, dt: float) -> float:
        v = float(raw)
        for s in self._steps:
            v = s.process(v, dt)
        return v

    def reset(self) -> None:
        for s in self._steps:
            s.reset()

    def tunable_params(self):
        out = []
        for i, s in enumerate(self._steps, 1):
            for tgt, name, spec, _ in s.tunable_params():
                out.append((tgt, name, spec, f"{i}{type(s).__name__} · "))
        return out
