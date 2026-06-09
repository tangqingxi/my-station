# core/registry.py · 带参装饰器 + 全局注册表

REGISTRY: dict[str, type] = {}


def register(name: str):
    """装饰器工厂：先收名字，返回 deco；deco 收类挂表，原样返回类。"""
    def deco(cls):
        # 同名注册通常是配置或 import 顺序问题，直接报出已占用的类。
        if name in REGISTRY:
            old_cls = REGISTRY[name]
            raise ValueError(
                f"重复注册：{name!r} 已被 {old_cls.__module__}.{old_cls.__name__} 占用"
            )
        REGISTRY[name] = cls
        return cls

    return deco
