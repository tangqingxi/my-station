# endpoints/modbus_sim_station.py · 一个 TCP 端口装多台 SimDevice · ★ v3 新增
# 职责只两件:1) 管 TCP 协议栈生命周期  2) 管多台 SimDevice 容器(add_device/去重)
import asyncio
import logging
import socket
import threading

from .modbus_sim_device import ModbusSimDevice

log = logging.getLogger(__name__)


class ModbusSimStation:
    def __init__(self, *, host: str = "0.0.0.0", port: int = 5020):
        self.host = str(host)
        self.port = int(port)
        self._devices: list[ModbusSimDevice] = []
        self._server = None
        self._loop = None
        self._thread = None
        self._started = False

    def add_device(self, dev: ModbusSimDevice) -> None:
        if self._started:
            raise RuntimeError("station 已启动,不能再 add_device")
        if dev.device_id in {d.device_id for d in self._devices}:
            raise ValueError(
                f"device_id={dev.device_id} 已被另一台 device 占用 "
                f"(已挂载 device_id={[d.device_id for d in self._devices]})"
            )
        self._devices.append(dev)

    @property
    def devices(self) -> list[ModbusSimDevice]:
        return list(self._devices)

    def start(self) -> None:
        if self._started:
            return
        if not self._devices:
            raise RuntimeError("Station 还没 add_device · 至少需要一台 device 才能 start")
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.bind((self.host, self.port))
        except OSError as e:
            raise RuntimeError(
                f"端口 {self.host}:{self.port} 已被占用 ({e})。"
                f"用 `Get-NetTCPConnection -LocalPort {self.port}` 查 PID,"
                f"再 `Stop-Process -Id <PID> -Force` 清掉旧的 server。"
            ) from None
        finally:
            probe.close()

        from pymodbus.server import ModbusTcpServer

        # ★ 关键:每台 device 各组一份 SimDevice,收成 list 喂给 server,自动按 device_id 路由
        sim_devices = [d.to_pymodbus_sim_device() for d in self._devices]

        loop = asyncio.new_event_loop()
        self._loop = loop
        ready = threading.Event()
        startup_error: list[BaseException] = []

        async def _run():
            try:
                self._server = ModbusTcpServer(context=sim_devices, address=(self.host, self.port))
            except Exception as e:
                startup_error.append(e)
                ready.set()
                return
            serve_task = asyncio.create_task(self._server.serve_forever())
            await asyncio.sleep(0.3)
            if serve_task.done():
                exc = serve_task.exception()
                if exc is not None:
                    startup_error.append(exc)
                ready.set()
                return
            ready.set()
            try:
                await serve_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                log.error("ModbusSimStation serve_forever 异常退出: %s", e)

        def _th():
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_run())
            except Exception as e:
                log.debug("station loop exited: %s", e)
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for t in pending:
                        t.cancel()
                    if pending:
                        try:
                            loop.run_until_complete(
                                asyncio.wait_for(
                                    asyncio.gather(*pending, return_exceptions=True),
                                    timeout=0.3,
                                )
                            )
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_th, daemon=True, name="modbus-sim-station")
        self._thread.start()
        if not ready.wait(timeout=4.0):
            raise RuntimeError(f"ModbusSimStation {self.host}:{self.port} 启动超时")
        if startup_error:
            raise startup_error[0]
        self._started = True
        log.info("ModbusSimStation listening %s:%d (devices: %s)",
                 self.host, self.port, [d.device_id for d in self._devices])

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        if self._loop is not None and self._loop.is_running():
            if self._server is not None:
                try:
                    asyncio.run_coroutine_threadsafe(self._server.shutdown(), self._loop)
                except Exception:
                    pass
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=0.8)
        self._thread = None
        self._server = None
        self._loop = None