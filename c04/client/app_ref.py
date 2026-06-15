# client/app_ref.py · v3 客户端参考实现(完整可跑)
#
# 跟 v2 的区别:
#   - 读独立的 client_config.toml (不再跟 server 共享 config)
#   - 从 [box].device_id 知道自己控哪台箱,传给 endpoint
#   - 窗口标题带 box-N · 让学生一眼知道自己在玩哪台
#   - Y 轴随实测温度动态长高:box-50 冲到 146°C 也完整画下,不依赖抄来的参数对不对
#   - 参数面板改为可选:client 默认是观察者/控制者、不是设计者,所以 server 端 plant
#     物理参数对它不是必需;client_config 的 [box] 若抄了参数就显示面板,没抄就只画曲线
#
# 链路(C3 切面):
#   ModbusTcpClient ── ModbusSensorEndpoint(role='client').read()  → 实时绘图
#                  └─ ModbusActuatorEndpoint(role='client').write() ← 按钮回调
#
# ★ C4 在此往上加 Sensor → FilteredSensor → SignalProcessor

from __future__ import annotations

from collections import deque
import sys
import tomllib
from pathlib import Path

import matplotlib
# Windows 中文显示:sans 和 monospace 两套都要带中文回退,负号回退到 ASCII '-'
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["font.monospace"] = ["Consolas", "Microsoft YaHei", "SimHei", "DejaVu Sans Mono"]
matplotlib.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, Slider

# 确保能 import 同级 core/ endpoints/ 包
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 注册子类(让 REGISTRY 填满)
import endpoints.modbus_sensor_endpoint  # noqa: F401
import endpoints.modbus_actuator_endpoint  # noqa: F401
import endpoints.mqtt_sensor_endpoint  # noqa: F401
import endpoints.mqtt_actuator_endpoint  # noqa: F401
import client.signal_processors  # noqa: F401

from core.factory import build
from client.box_context import ClientBoxContext
from client.filtered_sensor import EndpointSensor, FilteredSensor
# 客户端自己保管温度箱的物理常识 · 不依赖 server 模块(client 是独立部署的)
from client.thermal_info import compute_derived, format_model_params


def main(cfg_path: Path) -> None:
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    host = cfg["server"]["host"]
    port = cfg["server"]["port"]
    box_cfg = cfg["box"]
    device_id = int(box_cfg["device_id"])
    # 可选:学生从 server banner 抄过来的物理参数,有则显示面板
    has_params = "plant" in box_cfg and "actuator" in box_cfg

    # 统一 build → bind(ctx) → start：换传输只改 client_config 的 type 和 params。
    ctx = ClientBoxContext(device_id, host, port)
    sensor_ep = build(box_cfg["sensor_endpoint"], role="client")
    actuator_ep = build(box_cfg["actuator_endpoint"], role="client")
    sensor_ep.bind(ctx)
    actuator_ep.bind(ctx)
    sensor_ep.start()
    actuator_ep.start()

    # 启动时显式把这台箱的加热器置 OFF · UI 跟 server 真实状态对齐
    actuator_ep.write(False)
    print(f"[client] 已连接 {host}:{port} · 控制 box-{device_id}")

    sp_cfg = cfg.get("signal_processor")
    chain = None
    inner = EndpointSensor(sensor_ep)
    if sp_cfg is not None:
        processor = build(sp_cfg)
        dt_filter = float(cfg.get("loop", {}).get("dt_s", 0.5))
        chain = FilteredSensor(inner, processor, dt_filter)
    oversample = max(1, int(cfg.get("loop", {}).get("oversample", 1)))
    dt_ctrl = float(cfg.get("loop", {}).get("dt_s", 0.5))
    sub_dt = dt_ctrl / oversample
    sub_buf: deque[float] = deque(maxlen=oversample)
    subtick = {"n": 0}
    denoise = chain is not None or oversample > 1

    def _median(buf) -> float:
        s = sorted(buf)
        return float(s[len(s) // 2])

    # 绘图状态
    ts: list[int] = []
    temps: list[float] = []
    temps_filt: list[float] = []
    heater_on = {"v": False}

    # 有参数面板时图做宽,右侧留 32% 给面板;否则窄图布局
    if has_params:
        fig, ax = plt.subplots(figsize=(9.5, 5.0))
        fig.subplots_adjust(left=0.10, right=0.66, top=0.90, bottom=0.15)
    else:
        fig, ax = plt.subplots(figsize=(8.0, 5.0))
        fig.subplots_adjust(left=0.12, right=0.95, top=0.90, bottom=0.18)
    if denoise:
        filt_label = type(chain.processor).__name__ if chain is not None else f"median x{oversample}"
        line, = ax.plot([], [], "-", color="#bbbbbb", linewidth=0.8, label="noisy(原始)")
        line_filt, = ax.plot(
            [], [], "b-", linewidth=1.6,
            label=f"filtered({filt_label})",
        )
        ax.legend(loc="upper right", fontsize=8)
    else:
        line, = ax.plot([], [], "b-")
        line_filt = None
    ax.set_xlabel("tick")
    ax.set_ylabel("温度 / C")
    # Y 轴起步给个默认范围 · 真实上下限在 on_tick 里随实测温度动态撑开(不依赖抄来的参数)
    ax.set_ylim(20, 110)
    ax.grid(True, alpha=0.3)
    fig.canvas.manager.set_window_title(f"box-{device_id} · C3 v3 client")

    # 右侧参数面板 + T_ss 红线参考(可选,跟 v2 同形)
    if has_params:
        d = compute_derived(box_cfg)
        fig.text(
            0.68, 0.92, format_model_params(box_cfg),
            family="monospace", fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f3f3f3", edgecolor="#888"),
        )
        # 把目标稳态画成红色虚线 · 学生一眼看到该收敛到哪
        ax.axhline(d["t_ss"], color="r", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.text(2, d["t_ss"] + 1, f"T_ss = {d['t_ss']:.1f} C", color="r", fontsize=8)

    Y_PAD = 8.0  # Y 轴上下留白

    def on_tick(_frame):
        try:
            if oversample > 1:
                sub_buf.append(inner.read())
                subtick["n"] += 1
                if subtick["n"] % oversample != 0:
                    return (line,) if line_filt is None else (line, line_filt)
                raw = sub_buf[-1]
                measure = _median(sub_buf)
                filt = chain.processor.process(measure, dt_ctrl) if chain is not None else measure
                if chain is not None:
                    chain.last_raw = float(raw)
                    chain.last_filtered = float(filt)
            elif chain is not None:
                filt = chain.read()
                raw = chain.last_raw
            else:
                raw = sensor_ep.read()
                filt = None
        except IOError as e:
            ax.set_title(f"box-{device_id} · 读温度失败: {e}")
            return (line,) if line_filt is None else (line, line_filt)
        if raw is None:
            return (line,) if line_filt is None else (line, line_filt)
        ts.append(len(ts))
        temps.append(raw)
        line.set_data(ts[-120:], temps[-120:])
        if chain is not None and filt is not None:
            temps_filt.append(filt)
            line_filt.set_data(ts[-120:], temps_filt[-120:])
        if ts:
            ax.set_xlim(max(0, ts[-1] - 120), max(120, ts[-1]))
        # Y 轴随实测温度动态长高:温度快顶到上边就抬高上限 · 只升不降,绘图不抖
        ymin, ymax = ax.get_ylim()
        y_probe = max(raw, filt if filt is not None else raw)
        if y_probe + Y_PAD > ymax:
            ax.set_ylim(ymin, y_probe + 2 * Y_PAD)
        ax.set_title(
            f"box-{device_id}  noisy={raw:.1f}"
            + (f" → filtered={filt:.1f}" if chain is not None and filt is not None else "")
            + f"  加热器={'ON' if heater_on['v'] else 'OFF'}"
        )
        return (line,) if line_filt is None else (line, line_filt)

    def on_toggle(_event):
        heater_on["v"] = not heater_on["v"]
        actuator_ep.write(heater_on["v"])

    # 去噪滑条：从 tunable_params() 反射出可调参数，业务层不硬编码滤波器类型。
    sliders = []
    tunable = chain.processor.tunable_params() if chain is not None else []
    if tunable:
        nyquist = 0.5 / float(cfg.get("loop", {}).get("dt_s", 0.5))
        fig.subplots_adjust(bottom=0.12 + 0.07 * len(tunable))
        for i, (tgt, name, spec, prefix) in enumerate(tunable):
            sax = fig.add_axes((0.30, 0.04 + 0.07 * i, 0.40, 0.03))
            lo, hi = spec["range"]
            if spec.get("unit") == "Hz":
                hi = max(lo, min(hi, nyquist))
            init = max(lo, min(hi, getattr(tgt, name)))
            lbl = prefix + spec.get("label", name) + (f" / {spec['unit']}" if spec.get("unit") else "")
            sld = Slider(
                sax, lbl, float(lo), float(hi),
                valinit=init, valstep=spec.get("step"),
            )

            def _make(target, nm):
                def _cb(val):
                    target.set_params(**{nm: val})
                    chain.processor.reset()
                return _cb

            sld.on_changed(_make(tgt, name))
            sliders.append(sld)
        bax = fig.add_axes((0.80, 0.04, 0.16, 0.05))
    elif has_params:
        bax = fig.add_axes((0.72, 0.05, 0.22, 0.07))
    else:
        bax = fig.add_axes((0.40, 0.03, 0.20, 0.07))
    btn = Button(bax, "开 / 关加热器")
    btn.on_clicked(on_toggle)

    ani = FuncAnimation(fig, on_tick, interval=max(1, int(sub_dt * 1000)), cache_frame_data=False)
    plt.show()
    sensor_ep.stop()
    actuator_ep.stop()


if __name__ == "__main__":
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "client_config.toml"
    if not cfg_path.is_absolute():
        cfg_path = ROOT / cfg_path
    main(cfg_path)
