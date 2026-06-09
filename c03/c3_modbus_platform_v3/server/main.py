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
import endpoints.modbus_sensor_endpoint           # noqa
import endpoints.modbus_actuator_endpoint         # noqa

from core.factory import build, build_plant, build_sensor, build_actuator
from server.thermal_plant import format_box_summary
from endpoints.modbus_sim_device import ModbusSimDevice
from endpoints.modbus_sim_station import ModbusSimStation


def assemble_box(box_cfg: dict) -> dict:
    plant    = build_plant(box_cfg["plant"])
    sensor   = build_sensor(box_cfg["sensor"])
    actuator = build_actuator(box_cfg["actuator"])
    sim_dev = ModbusSimDevice(device_id=box_cfg["device_id"])
    sep = build(box_cfg["sensor_endpoint"],   role="server", slave=sim_dev, device_id=sim_dev.device_id)
    aep = build(box_cfg["actuator_endpoint"], role="server", slave=sim_dev, device_id=sim_dev.device_id)
    sep.start(); aep.start()
    return {"name": box_cfg["name"], "device_id": box_cfg["device_id"], "plant": plant,
            "sensor": sensor, "actuator": actuator, "sep": sep, "aep": aep,
            "sim_dev": sim_dev, "_cfg": box_cfg}


def main(cfg_path: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    logging.getLogger("pymodbus").setLevel(logging.ERROR)
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))

    sc = cfg["server"]
    station = ModbusSimStation(host=sc.get("bind", "0.0.0.0"), port=sc.get("port", 5020))

    boxes = []
    for box_cfg in cfg.get("box", []):
        b = assemble_box(box_cfg)
        station.add_device(b["sim_dev"])
        boxes.append(b)
    if not boxes:
        raise RuntimeError("config.toml 里没找到任何 [[box]],至少需要 1 台")

    station.start()

    dt = float(cfg.get("loop", {}).get("dt_s", 0.1))
    print("=" * 70)
    print(f"[ ModbusSimStation listening {station.host}:{station.port} ]")
    for b in boxes:
        print(format_box_summary(b["_cfg"]))
    print("=" * 70)
    print(f"[server] {len(boxes)} 台箱已就绪 · 主循环 dt = {dt} s · 等待客户端…")

    _ctrlc = {"n": 0}
    def _on_sigint(_s, _f):
        _ctrlc["n"] += 1
        if _ctrlc["n"] == 1:
            print("\n[server] Ctrl-C,正在关…(再按一次强退)"); raise KeyboardInterrupt
        os._exit(0)
    signal.signal(signal.SIGINT, _on_sigint)

    try:
        while True:
            for b in boxes:
                try:
                    cmd = b["aep"].poll_command()
                    if cmd is not None:
                        b["actuator"].apply(b["plant"], cmd)
                    b["plant"].step(dt)
                    b["sep"].update(b["sensor"].read(b["plant"]))
                except Exception as e:
                    logging.getLogger("box").error("%s (device_id=%d) step 异常: %s",
                                                   b["name"], b["device_id"], e)
            time.sleep(dt)
    except KeyboardInterrupt:
        pass
    finally:
        for b in boxes:
            b["sep"].stop(); b["aep"].stop()
        station.stop()
        print("[server] 已退出")


if __name__ == "__main__":
    main(Path(__file__).resolve().parent.parent / "config.toml")