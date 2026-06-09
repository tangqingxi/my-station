# endpoints/modbus_actuator_endpoint.py · 加热器开关 · 一类两用 · coil address=0, bool
import queue

from core.base_endpoint import BaseActuatorEndpoint
from core.registry import register

from .modbus_sim_device import ModbusSimDevice


@register("ModbusActuatorEndpoint")
class ModbusActuatorEndpoint(BaseActuatorEndpoint):
    def __init__(self, name="heater_ep", *, role="server", coil_address=0,
                 device_id=1, slave: ModbusSimDevice | None = None, client=None):
        super().__init__(name, role)
        self._coil = int(coil_address)
        self._device_id = int(device_id)
        self._slave = slave
        self._client = client
        self._cmd_q: queue.Queue = queue.Queue(maxsize=100)

    def attach_client(self, client) -> None:
        self._check_role("client", "attach_client")
        self._client = client

    def start(self) -> None:
        if self.role == "server":
            self._register_to_slave()
        else:
            if self._client is None:
                raise RuntimeError(f"{self.name!r} role='client' 但还没 attach ModbusTcpClient")
        self._running = True

    def stop(self) -> None:
        self._running = False

    def poll_command(self):
        self._check_role("server", "poll_command")
        latest = None
        while True:                       # 拿出所有积压，只保留最新一条（drop-old keep-latest）
            try:
                latest = self._cmd_q.get_nowait()
            except queue.Empty:
                break
        return latest

    def write(self, value) -> None:
        self._check_role("client", "write")
        # client 角色把开关命令写到 coil，任何传入值都按 Python bool 规则转换。
        self._client.write_coil(
            address=self._coil,
            value=bool(value),
            device_id=self._device_id,
        )

    def _register_to_slave(self) -> None:
        if self._slave is None:
            raise RuntimeError(f"{self.name!r} role='server' 但没传 slave(ModbusSimDevice)")
        from pymodbus.simulator import SimData
        from pymodbus.simulator.simdata import DataType
        coil = self._coil
        sd_co = SimData(coil, count=1, values=[0], datatype=DataType.BITS)
        self._slave.register_block("coils", sd_co)
        cmd_q = self._cmd_q

        async def action(func_code, start_address, address, count, registers, values):
            if func_code not in (5, 15) or values is None:      # 写 coil(fc=5/15)
                return
            if address > coil or address + len(values) <= coil:
                return
            v = bool(values[coil - address])
            if cmd_q.full():
                try:
                    cmd_q.get_nowait()
                except queue.Empty:
                    pass
            try:
                cmd_q.put_nowait(v)
            except queue.Full:
                pass

        self._slave.register_action(action)
