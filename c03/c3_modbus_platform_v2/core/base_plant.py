# core/base_plant.py · 物理模型基类(服务端跑数字孪生)
from abc import ABC, abstractmethod


class BasePlant(ABC):
    """物理模型基类 · 单线程主循环里跑."""

    SIGNATURE: dict = {"state": {}, "control": {}}   # 子类覆盖:声明状态/控制通道

    @abstractmethod
    def step(self, dt: float) -> None: ...
    @abstractmethod
    def get_state(self) -> dict: ...
    @abstractmethod
    def set_control(self, channel: str, value) -> None: ...