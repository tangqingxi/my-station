# server/simulated_temperature_sensor.py · 温度专用仿真传感器

from core.base_plant import BasePlant
from core.registry import register
from core.simulated_base_sensor import SimulatedBaseSensor


@register("SimulatedTemperatureSensor")
class SimulatedTemperatureSensor(SimulatedBaseSensor):
    def __init__(self, name="t1", *, noise_std=0.0, seed=None):
        super().__init__(name, noise_std=noise_std, seed=seed)

    def read(self, plant: BasePlant) -> float:
        v = plant.get_state()["temperature"]
        return self._add_noise(v)
