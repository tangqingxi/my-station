# server/thermal_plant.py · 单节点温度箱物理模型
# 模型:dT/dt = (eta*P - (T - T_env)/r_th) / c_heat
#   c_heat=15, eta=0.95, r_th=0.40, t_env=25 → 满功率 200W 稳态 ≈ 101°C(τ=6s)

from core.base_plant import BasePlant
from core.registry import register


@register("thermal")
class ThermalPlant(BasePlant):
    SIGNATURE = {
        "state": {"temperature": {"unit": "C", "range": [0.0, 200.0]}},
        "control": {"heat_power": {"unit": "W", "range": [0.0, 200.0]}},
    }

    def __init__(self, temp=25.0, c_heat=15.0, eta=0.95, r_th=0.40, t_env=25.0):
        self._temp = float(temp)
        self._heat_power = 0.0
        self._c_heat, self._eta = float(c_heat), float(eta)
        self._r_th, self._t_env = float(r_th), float(t_env)

    def step(self, dt: float) -> None:
        # 欧拉法推进温度：先算当前升温/散热速率，再按 dt 累加到温度上。
        d = (
            self._eta * self._heat_power
            - (self._temp - self._t_env) / self._r_th
        ) / self._c_heat
        self._temp += d * float(dt)

    def get_state(self) -> dict:
        return {"temperature": self._temp}

    def set_control(self, channel: str, value) -> None:
        # 据 SIGNATURE 校验控制通道：写错通道名当场报错，并列出合法清单
        if channel not in self.SIGNATURE["control"]:
            raise KeyError(
                f"未知控制通道 {channel!r}；本 plant 只认 {list(self.SIGNATURE['control'])}"
            )
        self._heat_power = float(value)  # 限幅不在这做，信任传入值


# ---- 本 plant 专属的「参数 + 推导值」展示工具（阶段5 客户端面板要用，先一起粘）----
# 公式只属于 ThermalPlant，所以跟类放一起、不放 core/。

def compute_derived(cfg: dict) -> dict:
    """从 cfg 算出物理推导值：时间常数 τ、满功率稳态 T_ss、起步升温率。"""
    p = cfg["plant"]["params"]
    a = cfg["actuator"]["params"]
    c_heat = float(p.get("c_heat", 15.0))
    eta = float(p.get("eta", 0.95))
    r_th = float(p.get("r_th", 0.40))
    t_env = float(p.get("t_env", 25.0))
    p_max = float(a.get("max_power", 200.0))
    return {
        "c_heat": c_heat,
        "eta": eta,
        "r_th": r_th,
        "t_env": t_env,
        "p_max": p_max,
        "tau": c_heat * r_th,               # 时间常数 s
        "t_ss": t_env + eta * p_max * r_th, # 满功率稳态 °C
        "rate0": eta * p_max / c_heat,      # 25°C 处升温率 °C/s
    }


def format_model_params(cfg: dict) -> str:
    """ASCII-only 多行参数面板，server banner / client monospace 标注共用。"""
    d = compute_derived(cfg)
    return (
        "[ Model Params ]\n"
        f"  c_heat = {d['c_heat']:>7.1f} J/K\n"
        f"  eta    = {d['eta']:>7.2f}\n"
        f"  r_th   = {d['r_th']:>7.2f} K/W\n"
        f"  t_env  = {d['t_env']:>7.1f} C\n"
        f"  P_max  = {d['p_max']:>7.1f} W\n"
        "\n"
        "[ Derived ]\n"
        f"  tau    = c_heat * r_th     = {d['tau']:>6.1f} s\n"
        f"  T_ss   = t_env + eta*P*r_th = {d['t_ss']:>6.1f} C\n"
        f"  rate0  = eta * P / c_heat   = {d['rate0']:>6.3f} C/s"
    )

def format_box_summary(box_cfg: dict) -> str:
    """server banner 用的单行摘要 · 给一台箱写一行."""
    d = compute_derived(box_cfg)
    return (
        f"  {box_cfg['name']:<8} device_id={box_cfg['device_id']:<3} "
        f"c_heat={d['c_heat']:>6.1f}  tau={d['tau']:>6.1f}s  T_ss={d['t_ss']:>6.1f}C"
    )