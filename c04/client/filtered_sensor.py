# client/filtered_sensor.py · 去噪链 · Sensor → FilteredSensor → SignalProcessor
from __future__ import annotations

from core.base_endpoint import BaseSensorEndpoint
from core.base_signal_processor import BaseSignalProcessor


class EndpointSensor:
    """把 client 端点包成只暴露 read() 的传感器。"""

    def __init__(self, endpoint: BaseSensorEndpoint):
        self._ep = endpoint

    def read(self) -> float:
        return float(self._ep.read())


class FilteredSensor:
    """读内层传感器，再交给 SignalProcessor 去噪。"""

    def __init__(self, inner, processor: BaseSignalProcessor, dt: float):
        self._inner = inner
        self._proc = processor
        self._dt = float(dt)
        self.last_raw: float | None = None
        self.last_filtered: float | None = None

    @property
    def processor(self) -> BaseSignalProcessor:
        return self._proc

    def read(self) -> float:
        raw = self._inner.read()
        filtered = self._proc.process(raw, self._dt)
        self.last_raw = float(raw)
        self.last_filtered = float(filtered)
        return self.last_filtered

    def reset(self) -> None:
        self._proc.reset()
        self.last_raw = None
        self.last_filtered = None
