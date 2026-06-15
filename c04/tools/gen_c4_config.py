# tools/gen_c4_config.py · 生成 C4 演示用 server 配置 · N 箱 · MQTT 传输 · 可选逐箱随机噪声
#   uv run python tools/gen_c4_config.py            → config_c4.toml
#   uv run python tools/gen_c4_config.py --noise    → config_c4_noisy.toml
import random
import sys
from pathlib import Path

N = 50
BASE_SEED = 2025
EMIT_DT = 0.5
ROOT = Path(__file__).resolve().parent.parent
OUT_NONOISE = ROOT / "config_c4.toml"
OUT_NOISY = ROOT / "config_c4_noisy.toml"

HEADER = """# {out} · C4 演示 server 配置 · {n} 箱 · MQTT 传输{tag}
# 由 tools/gen_c4_config.py 生成；要改规模或噪声，请改脚本后重跑。
[server]
bind = "0.0.0.0"
port = 5020

[loop]
dt_s = 0.1
emit_dt_s = {emit}
sample_dt_s = 0.1
"""


def inline(d: dict) -> str:
    """dict → TOML 内联表；值须已是 TOML 字面量字符串。"""
    return "{ " + ", ".join(f"{k} = {v}" for k, v in d.items()) + " }"


def src(typ: str, params: dict) -> str:
    return inline({"type": f'"{typ}"', "params": inline(params)})


def random_noise(rng: random.Random, did: int) -> str:
    """逐箱随机抽取 2 到 3 种噪声，阶段三开始使用。"""
    pool = ["gauss", "sine", "impulse"]
    picks = rng.sample(pool, rng.randint(2, 3))
    sources = []
    for p in picks:
        if p == "gauss":
            sources.append(src("GaussianNoise", {
                "std": round(rng.uniform(0.2, 0.8), 2), "seed": did}))
        elif p == "sine":
            sources.append(src("SineNoise", {
                "amplitude": round(rng.uniform(0.3, 1.2), 2),
                "freq_hz": rng.choice([0.5, 1.0, 1.5, 2.0]),
                "phase": round(rng.uniform(0.0, 6.28), 2), "dt": EMIT_DT}))
        elif p == "impulse":
            sources.append(src("ImpulseNoise", {
                "prob": round(rng.uniform(0.05, 0.12), 3),
                "amplitude": round(rng.uniform(2.0, 6.0), 1), "seed": did}))
    return src("CompositeNoise", {"sources": "[ " + ", ".join(sources) + " ]"})


def box_block(did: int, with_noise: bool) -> str:
    t_env = float(20 + did)
    if with_noise:
        rng = random.Random(BASE_SEED * 1000 + did)
        sensor_params = f'name = "t{did}", noise = {random_noise(rng, did)}'
    else:
        sensor_params = f'name = "t{did}"'
    return "\n".join([
        "[[box]]",
        f'name = "box-{did}"',
        f"device_id = {did}",
        f'plant             = {{ type = "thermal", params = {{ temp = 25.0, c_heat = 15.0, eta = 0.95, r_th = 0.40, t_env = {t_env:.1f} }} }}',
        f'sensor            = {{ type = "SimulatedTemperatureSensor", params = {{ {sensor_params} }} }}',
        f'actuator          = {{ type = "SimulatedHeaterActuator", params = {{ name = "h{did}", channel = "heat_power", max_power = 200.0 }} }}',
        f'sensor_endpoint   = {{ type = "MqttSensorEndpoint",   params = {{ name = "sep{did}", topic = "my-station/sensor/box-{did}" }} }}',
        f'actuator_endpoint = {{ type = "MqttActuatorEndpoint", params = {{ name = "aep{did}", topic = "my-station/actuator/box-{did}/cmd" }} }}',
    ])


def main() -> None:
    with_noise = "--noise" in sys.argv[1:]
    out = OUT_NOISY if with_noise else OUT_NONOISE
    tag = " · 逐箱随机叠加噪声" if with_noise else " · 无噪"
    parts = [HEADER.format(out=out.name, n=N, tag=tag, emit=EMIT_DT)]
    parts += [box_block(d, with_noise) for d in range(1, N + 1)]
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"已生成 {out.name} · {N} 箱 · MQTT · {'逐箱随机叠加噪声' if with_noise else '无噪'}")


if __name__ == "__main__":
    main()
