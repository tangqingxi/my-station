# endpoints/modbus_sim_device.py · 一台 Modbus 模拟设备(单 device_id + 自带 TCP 协议栈)
import asyncio
import logging
import socket
import threading
from typing import Callable

log = logging.getLogger(__name__)


class ModbusSimDevice:
    def __init__(self, *, host="0.0.0.0", port=5020, device_id=1):
        self.host = str(host)
        self.port = int(port)
        self.device_id = int(device_id)
        self._coils: list = []
        self._discrete_inputs: list = []
        self._holding: list = []
        self._input: list = []
        self._actions: list[Callable] = []  # async callable, 顺序派发
        self._server = None
        self._loop = None
        self._thread = None
        self._started = False

    def register_block(self, kind: str, sd) -> None:
        if self._started:
            raise RuntimeError("slave 已启动,不能再注册新 block")
        getattr(self, f"_{kind}").append(sd)

    def register_action(self, action_async: Callable) -> None:
        if self._started:
            raise RuntimeError("slave 已启动,不能再注册新 action")
        self._actions.append(action_async)

    def start(self) -> None:
        if self._started:
            return
        # 裸 socket 探测端口 —— pymodbus 3.13 在 Windows 上可能把 bind 错吞掉
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
        from pymodbus.simulator import SimData, SimDevice
        from pymodbus.simulator.simdata import DataType

        def _pad(lst, dummy):
            return lst if lst else [dummy]

        dummy_bit = SimData(0, count=1, values=[0], datatype=DataType.BITS)
        dummy_reg = SimData(0, count=1, values=[0], datatype=DataType.REGISTERS)
        simdata = (
            _pad(self._coils, dummy_bit),
            _pad(self._discrete_inputs, dummy_bit),
            _pad(self._holding, dummy_reg),
            _pad(self._input, dummy_reg),
        )
        actions = list(self._actions)

        async def dispatch(func_code, start_address, address, count, registers, values):
            for fn in actions:
                await fn(func_code, start_address, address, count, registers, values)
            return None

        device = SimDevice(id=self.device_id, simdata=simdata, action=dispatch)

        loop = asyncio.new_event_loop()
        self._loop = loop
        ready = threading.Event()
        startup_error: list[BaseException] = []

        async def _run():
            try:
                self._server = ModbusTcpServer(context=device, address=(self.host, self.port))
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
                log.error("ModbusSimDevice serve_forever 异常退出: %s", e)

        def _th():
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_run())
            except Exception as e:
                log.debug("slave loop exited: %s", e)
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

        self._thread = threading.Thread(target=_th, daemon=True, name="modbus-slave")
        self._thread.start()
        if not ready.wait(timeout=4.0):
            raise RuntimeError(f"ModbusSimDevice {self.host}:{self.port} 启动超时")
        if startup_error:
            raise startup_error[0]
        self._started = True
        log.info("ModbusSimDevice listening %s:%d device_id=%d", self.host, self.port, self.device_id)

    def stop(self) -> None:
        """快速关闭:fire-and-forget,直接停 loop,daemon 线程靠进程退出收割."""
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