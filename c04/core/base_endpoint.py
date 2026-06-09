# core/base_endpoint.py · Endpoint 一类两用 · role 区分 server / client
from abc import ABC, abstractmethod
from typing import Literal

Role = Literal["server", "client"]


class _RoleMixin:
    role: Role
    def _check_role(self, expected: Role, op: str) -> None:
        if self.role != expected:
            raise RuntimeError(
                f"{type(self).__name__}.{op}() 只能在 role={expected!r} 调用 (当前 role={self.role!r})"
            )


class BaseSensorEndpoint(ABC, _RoleMixin):
    """server 推 update(v) · client 拉 read()→float."""
    def __init__(self, name: str, role: Role):
        self.name, self.role, self._running = name, role, False
    @abstractmethod
    def start(self) -> None: ...
    @abstractmethod
    def stop(self) -> None: ...
    @abstractmethod
    def update(self, value: float) -> None: ...
    @abstractmethod
    def read(self) -> float: ...


class BaseActuatorEndpoint(ABC, _RoleMixin):
    """server 拉 poll_command() · client 推 write(v)."""
    def __init__(self, name: str, role: Role):
        self.name, self.role, self._running = name, role, False
    @abstractmethod
    def start(self) -> None: ...
    @abstractmethod
    def stop(self) -> None: ...
    @abstractmethod
    def poll_command(self): ...
    @abstractmethod
    def write(self, value) -> None: ...