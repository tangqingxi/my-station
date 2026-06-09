# server/main.py · 服务端主程序
from __future__ import annotations
import logging, os, signal, sys, time, tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server.thermal_plant                       # noqa: 触发 @register
import server.simulated_temperature_sensor        # noqa
import server.simulated_heater_actuator           # noqa
import endpoints.modbus_sensor_endpoint           # noqa
import endpoints.modbus_actuator_endpoint         # noqa

from core.factory import build, build_plant, build_sensor, build_actuator
from endpoints.modbus_sim_device import ModbusSimDevice


def main(cfg_path: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    logging.getLogger("pymodbus").setLevel(logging.ERROR)
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))

    plant = build_plant(cfg["plant"])
    sensor = build_sensor(cfg["sensor"])
    actuator = build_actuator(cfg["actuator"])

    sc = cfg["server"]
    slave = ModbusSimDevice(host=sc.get("bind", "0.0.0.0"), port=sc.get("port", 5020),
                            device_id=sc.get("device_id", 1))
    sensor_ep = build(cfg["sensor_endpoint"], role="server", slave=slave)
    actuator_ep = build(cfg["actuator_endpoint"], role="server", slave=slave)
    sensor_ep.start(); actuator_ep.start(); slave.start()

    dt = float(cfg.get("loop", {}).get("dt_s", 0.1))
    print(f"[server] 起在 {slave.host}:{slave.port} device_id={slave.device_id} · dt={dt}s · 等待客户端…")

    _ctrlc = {"n": 0}
    def _on_sigint(_s, _f):
        _ctrlc["n"] += 1
        if _ctrlc["n"] == 1:
            print("\n[server] Ctrl-C,正在关…(再按一次强退)"); raise KeyboardInterrupt
        os._exit(0)
    signal.signal(signal.SIGINT, _on_sigint)

    try:
        while True:
            cmd = actuator_ep.poll_command()
            if cmd is not None:
                actuator.apply(plant, cmd)
            plant.step(dt)
            sensor_ep.update(sensor.read(plant))
            time.sleep(dt)
    except KeyboardInterrupt:
        pass
    finally:
        sensor_ep.stop(); actuator_ep.stop(); slave.stop()
        print("[server] 已退出")


if __name__ == "__main__":
    main(Path(__file__).resolve().parent.parent / "config.toml")