# core/factory.py · 通用工厂 · 按 toml 字典反射建对象 · 不再写 if/elif
from .registry import REGISTRY
from .base_noise_source import NoiseSource, NullNoise


def build(cfg: dict, **extra):
    type_name = cfg["type"]
    if type_name not in REGISTRY:
        raise KeyError(f"未注册的 type={type_name!r} · 已注册：{list(REGISTRY)}")
    cls = REGISTRY[type_name]                       # 字符串 → 类（查表）
    params = {**cfg.get("params", {}), **extra}
    return cls(**params)                            # 类 → 对象（反射构造）


def build_plant(cfg):    return build(cfg)
def build_sensor(cfg):   return build(cfg)
def build_actuator(cfg): return build(cfg)


def build_noise(cfg) -> NoiseSource:
    """None→NullNoise；已是 NoiseSource→原样；{type,params}→工厂反射建。"""
    if cfg is None:
        return NullNoise()
    if isinstance(cfg, NoiseSource):
        return cfg
    return build(cfg)
