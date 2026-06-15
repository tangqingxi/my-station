from abc import ABC, abstractmethod
from typing import Literal

Role = Literal["server", "client"]


class BaseEndpoint(ABC):
    """端点基类：沉淀两类端点共同的构造、role 校验和生命周期。"""

    def __init__(self, name: str, role: Role):
        self.name = name
        self.role = role
        self._running = False

    def _check_role(self, expected: Role, op: str) -> None:
        if self.role != expected:
            raise RuntimeError(
                f"{type(self).__name__}.{op}() 只能在 role={expected!r} 调用 "
                f"(当前 role={self.role!r})"
            )

    def bind(self, ctx) -> None:
        """接入装配上下文，默认空操作。

        各传输按需覆写：服务端取共享资源，客户端按坐标自行连接。
        """
        return

    @abstractmethod
    def start(self) -> None: ...
    @abstractmethod
    def stop(self) -> None: ...


class BaseSensorEndpoint(BaseEndpoint):
    """Sensor 端点：server 推 update(v)，client 拉 read() 得到 float。"""

    @abstractmethod
    def update(self, value: float) -> None: ...
    @abstractmethod
    def read(self) -> float: ...


class BaseActuatorEndpoint(BaseEndpoint):
    """Actuator 端点：server 拉 poll_command()，client 推 write(v)。"""

    @abstractmethod
    def poll_command(self): ...
    @abstractmethod
    def write(self, value) -> None: ...
