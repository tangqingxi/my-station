# endpoints/modbus_sensor_endpoint.py · 温度通道 · 一类两用
# 线缆约定：温度在 holding register address=0，float32 占 2 个 register，big-endian
import threading

from pymodbus.client import ModbusTcpClient

from core.base_endpoint import BaseSensorEndpoint
from core.codec import f32_to_regs, regs_to_f32
from core.registry import register

from .modbus_sim_device import ModbusSimDevice


@register("ModbusSensorEndpoint")
class ModbusSensorEndpoint(BaseSensorEndpoint):
    def __init__(self, name="temp_ep", *, role="server", register_address=0,
                 device_id=1, slave: ModbusSimDevice | None = None, client=None):
        super().__init__(name, role)
        self._addr = int(register_address)
        self._device_id = int(device_id)
        self._slave = slave
        self._client = client
        self._lock = threading.Lock()
        self._latest: float | None = None

    def attach_client(self, client) -> None:
        self._check_role("client", "attach_client")
        self._client = client

    def bind(self, ctx) -> None:
        """服务端取本箱 SimDevice，客户端按 ctx 坐标自己建立 Modbus 连接。"""
        self._device_id = int(ctx.device_id)
        if self.role == "server":
            self._slave = ctx.modbus_device()
        else:
            mc = ModbusTcpClient(ctx.host, port=ctx.port, timeout=2.0)
            if not mc.connect():
                raise RuntimeError(f"连不上 Modbus 服务器 {ctx.host}:{ctx.port}")
            self._client = mc

    def start(self) -> None:
        if self.role == "server":
            self._register_to_slave()
        else:
            if self._client is None:
                raise RuntimeError(f"{self.name!r} role='client' 但还没绑定 ModbusTcpClient")
        self._running = True

    def stop(self) -> None:
        if self.role == "client" and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._running = False

    def update(self, value: float) -> None:
        self._check_role("server", "update")
        with self._lock:
            self._latest = float(value)

    def read(self) -> float:
        self._check_role("client", "read")
        # client 角色从 holding register 读取 2 个寄存器，再按 float32 还原温度。
        rr = self._client.read_holding_registers(
            address=self._addr,
            count=2,
            device_id=self._device_id,
        )
        if rr.isError():
            raise IOError(f"读温度失败：{rr}")
        return regs_to_f32(rr.registers)

    def _register_to_slave(self) -> None:
        if self._slave is None:
            raise RuntimeError(f"{self.name!r} role='server' 但没有绑定 slave(ModbusSimDevice)")
        from pymodbus.simulator import SimData
        from pymodbus.simulator.simdata import DataType
        addr = self._addr
        sd_hr = SimData(addr, count=2, values=[0, 0], datatype=DataType.REGISTERS)
        self._slave.register_block("holding", sd_hr)
        lock = self._lock

        async def action(func_code, start_address, address, count, registers, values):
            if func_code != 3 or values is not None:     # 只处理 holding read(fc=3)
                return
            with lock:
                v = self._latest
            if v is None:
                return
            if address > addr + 1 or address + count <= addr:
                return
            offset = addr - start_address
            registers[offset:offset + 2] = f32_to_regs(v)   # 即时把最新温度编进寄存器

        self._slave.register_action(action)
