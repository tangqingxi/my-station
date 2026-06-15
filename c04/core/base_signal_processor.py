# core/base_signal_processor.py · 信号处理基类 · 客户端去噪处理器家族
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from core.params_schema import ParamsSchema, get_current_params, validate_and_apply


class BaseSignalProcessor(ABC):
    PARAMS_SCHEMA: ClassVar[ParamsSchema] = {}

    @abstractmethod
    def process(self, raw: float, dt: float) -> float:
        """处理一个采样：输入原始信号，输出滤波后信号。"""

    def reset(self) -> None:
        return

    def set_params(self, **kwargs: Any) -> None:
        validate_and_apply(self, type(self).PARAMS_SCHEMA, kwargs)

    def get_params(self) -> dict[str, Any]:
        return get_current_params(self, type(self).PARAMS_SCHEMA)

    def tunable_params(self) -> list[tuple[Any, str, dict, str]]:
        """返回可由 UI 调节的参数：(target, name, spec, prefix)。"""
        return [
            (self, name, spec, "")
            for name, spec in type(self).PARAMS_SCHEMA.items()
            if "range" in spec and spec.get("type") in ("float", "int")
        ]
