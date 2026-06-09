# server/simulated_heater_actuator.py · 加热器仿真执行器 · 限幅在这里做

from core.base_plant import BasePlant
from core.simulated_base_actuator import SimulatedBaseActuator


class SimulatedHeaterActuator(SimulatedBaseActuator):
    def __init__(self, name="heater1", *, channel="heat_power", max_power=200.0, min_power=0.0):
        super().__init__(name, channel)
        if min_power > max_power:
            raise ValueError(f"min_power {min_power} > max_power {max_power}")
        self._min = float(min_power)
        self._max = float(max_power)

    def apply(self, plant: BasePlant, value) -> None:
        # bool 是 int 的子类，所以必须先处理开关命令，再处理数值功率命令。
        if isinstance(value, bool):
            p = self._max if value else self._min
        else:
            p = max(self._min, min(self._max, float(value)))
        plant.set_control(self.channel, p)
