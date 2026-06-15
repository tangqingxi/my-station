from __future__ import annotations

from core.base_signal_processor import BaseSignalProcessor
from core.registry import register


@register("IdentityProcessor")
class IdentityProcessor(BaseSignalProcessor):
    def process(self, raw: float, dt: float) -> float:
        return float(raw)
