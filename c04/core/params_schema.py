from __future__ import annotations

from typing import Any, Literal, TypedDict

ParamType = Literal["float", "int", "matrix", "enum"]


class ParamSpec(TypedDict, total=False):
    type: ParamType
    default: Any
    label: str
    range: list[float]
    step: float
    unit: str
    choices: list[Any]


ParamsSchema = dict[str, ParamSpec]


def validate_and_apply(obj, schema: ParamsSchema, kwargs: dict) -> None:
    for name, value in kwargs.items():
        if name not in schema:
            raise ValueError(f"未声明的参数 {name!r} · keys: {sorted(schema)}")
        t = schema[name].get("type", "float")
        if t == "float":
            _apply_num(obj, name, schema[name], value, float)
        elif t == "int":
            _apply_num(obj, name, schema[name], value, int)
        else:
            raise NotImplementedError(f"ParamSpec type={t!r} 未实现")


def _apply_num(obj, name, spec, value, caster):
    if caster is int and isinstance(value, float) and not value.is_integer():
        raise TypeError(f"参数 {name}={value!r} 不是整数")
    v = caster(value)
    rng = spec.get("range")
    if rng is not None:
        # 超量程时夹到边界，方便滑条和配置一起复用。
        v = max(caster(rng[0]), min(caster(rng[1]), v))
    setattr(obj, name, v)


def get_current_params(obj, schema: ParamsSchema) -> dict:
    return {name: getattr(obj, name) for name in schema}
