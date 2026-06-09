# endpoints/modbus_sim_device.py - 一台 Modbus 模拟设备(纯数据,不含 TCP)
# ★ v3 趋势:TCP/asyncio/thread 都挪到 ModbusSimStation。本类只管:
#   device_id + 4 类地址空间 + action 派发 + 一个 to_pymodbus_sim_device() 出口
import logging
from typing import Callable

log = logging.getLogger(__name__)


class ModbusSimDevice:
    def __init__(self, *, device_id: int):
        self.device_id = int(device_id)
        self._coils: list = []
        self._discrete_inputs: list = []
        self._holding: list = []
        self._input: list = []
        self._actions: list[Callable] = []

    def register_block(self, kind: str, sd) -> None:
        getattr(self, f"_{kind}").append(sd)

    def register_action(self, action_async: Callable) -> None:
        self._actions.append(action_async)

    def to_pymodbus_sim_device(self):
        """把累积的 SimData + action 组装成 pymodbus SimDevice(Station 在 start 时调)。"""
        from pymodbus.simulator import SimData, SimDevice
        from pymodbus.simulator.simdata import DataType

        dummy_bit = SimData(0, count=1, values=[0], datatype=DataType.BITS)
        dummy_reg = SimData(0, count=1, values=[0], datatype=DataType.REGISTERS)

        def _pad(lst, dummy):
            return lst if lst else [dummy]

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

        return SimDevice(id=self.device_id, simdata=simdata, action=dispatch)
