# server/main.py · v3 多箱版
from __future__ import annotations
import logging, os, signal, sys, time, tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server.thermal_plant                       # noqa
import server.simulated_temperature_sensor        # noqa
import server.simulated_heater_actuator           # noqa
import server.noise_sources                       # noqa
import endpoints.modbus_sensor_endpoint           # noqa
import endpoints.modbus_actuator_endpoint         # noqa
import endpoints.mqtt_sensor_endpoint             # noqa
import endpoints.mqtt_actuator_endpoint           # noqa

from core.factory import build, build_plant, build_sensor, build_actuator
from server.box_dashboard import BoxDashboard, serve as serve_dashboard
from server.thermal_plant import format_box_summary
from endpoints.modbus_sim_gateway import ModbusSimGateway
from server.box_context import ServerBoxContext


def assemble_box(box_cfg: dict, gateway) -> dict:
    """端点统一 build → bind → start；装配层不再认识具体传输。"""
    plant    = build_plant(box_cfg["plant"])
    sensor   = build_sensor(box_cfg["sensor"])
    actuator = build_actuator(box_cfg["actuator"])

    ctx = ServerBoxContext(box_cfg["device_id"], gateway)
    sep = build(box_cfg["sensor_endpoint"],   role="server")
    aep = build(box_cfg["actuator_endpoint"], role="server")
    sep.bind(ctx)
    aep.bind(ctx)
    sep.start(); aep.start()

    return {"name": box_cfg["name"], "device_id": box_cfg["device_id"], "plant": plant,
            "sensor": sensor, "actuator": actuator, "sep": sep, "aep": aep,
            "uses_modbus": ctx.uses_modbus, "_cfg": box_cfg}


def _command_power(actuator, cmd) -> float:
    """把当前命令换算成看板功率线；只作显示，不参与控制闭环。"""
    min_power = float(getattr(actuator, "_min", 0.0))
    max_power = float(getattr(actuator, "_max", 0.0))
    if isinstance(cmd, bool):
        return max_power if cmd else min_power
    try:
        return max(min_power, min(max_power, float(cmd)))
    except (TypeError, ValueError):
        return min_power


def main(cfg_path: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    logging.getLogger("pymodbus").setLevel(logging.ERROR)
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))

    sc = cfg["server"]
    gateway = ModbusSimGateway(host=sc.get("bind", "0.0.0.0"), port=sc.get("port", 5020))

    boxes = []
    for box_cfg in cfg.get("box", []):
        b = assemble_box(box_cfg, gateway)
        boxes.append(b)
    if not boxes:
        raise RuntimeError("config.toml 里没找到任何 [[box]],至少需要 1 台")

    gateway.start()

    dt = float(cfg.get("loop", {}).get("dt_s", 0.1))
    emit_dt = float(cfg.get("loop", {}).get("emit_dt_s", dt))
    emit_every = max(1, round(emit_dt / dt))
    sample_dt = float(cfg.get("loop", {}).get("sample_dt_s", emit_dt))
    sample_every = max(1, round(sample_dt / dt))
    dash = BoxDashboard(station_id="my-station")
    dash_host = sc.get("dashboard_host", "127.0.0.1")
    dash_port = int(sc.get("dashboard_port", 5400))
    serve_dashboard(dash, host=dash_host, port=dash_port)

    print("=" * 70)
    print(gateway.status_line())
    for b in boxes:
        print(format_box_summary(b["_cfg"]))
    print("=" * 70)
    print(f"[server] 看板(真值 vs 加噪):http://{dash_host}:{dash_port}/  ← 浏览器打开,下拉选箱")
    print(
        f"[server] {len(boxes)} 台箱已就绪 · 主循环 dt = {dt} s · "
        f"sample_dt = {sample_dt} s · emit_dt = {emit_dt} s · 等待客户端…"
    )

    _ctrlc = {"n": 0}
    def _on_sigint(_s, _f):
        _ctrlc["n"] += 1
        if _ctrlc["n"] == 1:
            print("\n[server] Ctrl-C,正在关…(再按一次强退)"); raise KeyboardInterrupt
        os._exit(0)
    signal.signal(signal.SIGINT, _on_sigint)

    step_i = 0
    u_now: dict[str, float] = {}
    noisy_now: dict[str, float | None] = {b["name"]: None for b in boxes}
    try:
        while True:
            sample = (step_i % sample_every == 0)
            emit = (step_i % emit_every == 0)
            for b in boxes:
                try:
                    cmd = b["aep"].poll_command()
                    if cmd is not None:
                        b["actuator"].apply(b["plant"], cmd)
                        u_now[b["name"]] = _command_power(b["actuator"], cmd)
                    b["plant"].step(dt)
                    if sample:
                        noisy = b["sensor"].read(b["plant"])
                        b["sep"].update(noisy)
                        noisy_now[b["name"]] = noisy
                    if emit:
                        true_v = b["plant"].get_state()["temperature"]
                        noisy0 = noisy_now[b["name"]]
                        if noisy0 is None:
                            noisy0 = b["sensor"].read(b["plant"])
                        dash.record(b["name"], true_v, noisy0, u_now.get(b["name"], 0.0))
                except Exception as e:
                    logging.getLogger("box").error("%s (device_id=%d) step 异常: %s",
                                                   b["name"], b["device_id"], e)
            step_i += 1
            time.sleep(dt)
    except KeyboardInterrupt:
        pass
    finally:
        for b in boxes:
            b["sep"].stop(); b["aep"].stop()
        gateway.stop()
        print("[server] 已退出")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "config.toml"
    if not cfg_path.is_absolute():
        cfg_path = root / cfg_path
    main(cfg_path)
