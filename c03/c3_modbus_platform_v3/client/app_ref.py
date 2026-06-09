# client/app_ref.py · 客户端(完整可跑)· 用核心 endpoint(role='client')
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["font.monospace"] = ["Consolas", "Microsoft YaHei", "SimHei", "DejaVu Sans Mono"]
matplotlib.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from pymodbus.client import ModbusTcpClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 注册子类(让 REGISTRY 填满)
import endpoints.modbus_sensor_endpoint  # noqa: F401
import endpoints.modbus_actuator_endpoint  # noqa: F401

from core.factory import build
# 参数面板的公式是 ThermalPlant 专属,从 plant 文件 import(v3 才改成客户端自带)
from server.thermal_plant import compute_derived, format_model_params


def main() -> None:
    cfg = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
    host = cfg["server"]["host"]
    port = cfg["server"]["port"]

    modbus_client = ModbusTcpClient(host, port=port, timeout=2.0)
    if not modbus_client.connect():
        raise RuntimeError(f"连不上 Modbus 服务器 {host}:{port}")
    print(f"[client] 已连接 {host}:{port}")

    # 反射建 endpoint · role='client' · 调的就是你在阶段4 写的 read/write
    sensor_ep = build(cfg["sensor_endpoint"], role="client", client=modbus_client)
    actuator_ep = build(cfg["actuator_endpoint"], role="client", client=modbus_client)
    sensor_ep.start()
    actuator_ep.start()

    actuator_ep.write(False)   # 启动同步 OFF,UI 跟 server 真实状态对齐

    ts: list[int] = []
    temps: list[float] = []
    heater_on = {"v": False}

    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    fig.subplots_adjust(left=0.10, right=0.66, top=0.90, bottom=0.12)
    line, = ax.plot([], [], "b-")
    ax.set_xlabel("tick")
    ax.set_ylabel("温度 / C")
    ax.set_ylim(20, 110)
    ax.grid(True, alpha=0.3)

    d = compute_derived(cfg)
    fig.text(
        0.68, 0.92, format_model_params(cfg),
        family="monospace", fontsize=9, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f3f3f3", edgecolor="#888"),
    )
    ax.axhline(d["t_ss"], color="r", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(2, d["t_ss"] + 1, f"T_ss = {d['t_ss']:.1f} C", color="r", fontsize=8)

    def on_tick(_frame):
        try:
            t = sensor_ep.read()
        except IOError as e:
            ax.set_title(f"读温度失败: {e}")
            return (line,)
        ts.append(len(ts))
        temps.append(t)
        line.set_data(ts[-120:], temps[-120:])
        if ts:
            ax.set_xlim(max(0, ts[-1] - 120), max(120, ts[-1]))
        ax.set_title(f"温度 = {t:.1f} C   加热器 = {'ON' if heater_on['v'] else 'OFF'}")
        return (line,)

    def on_toggle(_event):
        heater_on["v"] = not heater_on["v"]
        actuator_ep.write(heater_on["v"])

    bax = fig.add_axes((0.72, 0.05, 0.22, 0.08))
    btn = Button(bax, "开 / 关加热器")
    btn.on_clicked(on_toggle)

    ani = FuncAnimation(fig, on_tick, interval=500, cache_frame_data=False)
    plt.show()
    sensor_ep.stop()
    actuator_ep.stop()
    modbus_client.close()


if __name__ == "__main__":
    main()