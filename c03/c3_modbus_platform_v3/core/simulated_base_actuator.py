# core/simulated_base_actuator.py · 服务端「仿真执行」基类 · 跟 Sensor 对称 · 只对 plant 负责
from abc import ABC, abstractmethod
from .base_plant import BasePlant


class SimulatedBaseActuator(ABC):
    def __init__(self, name: str, channel: str):
        self.name = name
        self.channel = channel

    @abstractmethod
    def apply(self, plant: BasePlant, value) -> None:
        """把 value 写到 plant.set_control(self.channel, value);子类在此做限幅/换算."""