# client/thermal_info.py · 客户端自己保管的温度箱物理常识 · 不 import server
# 公式跟 server/thermal_plant.py 同形,但语义是「客户端自己掌握的」。


def compute_derived(box_cfg: dict) -> dict:
    p = box_cfg["plant"]["params"]
    a = box_cfg["actuator"]["params"]
    c_heat = float(p.get("c_heat", 15.0))
    eta = float(p.get("eta", 0.95))
    r_th = float(p.get("r_th", 0.40))
    t_env = float(p.get("t_env", 25.0))
    p_max = float(a.get("max_power", 200.0))
    return {"c_heat": c_heat, "eta": eta, "r_th": r_th, "t_env": t_env, "p_max": p_max,
            "tau": c_heat * r_th, "t_ss": t_env + eta * p_max * r_th, "rate0": eta * p_max / c_heat}


def format_model_params(box_cfg: dict) -> str:
    d = compute_derived(box_cfg)
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