# server/box_context.py · 服务端装配上下文 · 管理本箱共享的传输资源
from endpoints.modbus_sim_device import ModbusSimDevice


class ServerBoxContext:
    def __init__(self, device_id, gateway):
        self.device_id = int(device_id)
        self._gateway = gateway
        self._sim_dev = None

    def modbus_device(self) -> ModbusSimDevice:
        """懒建本箱唯一的 SimDevice，并在首次创建时挂到网关。"""
        if self._sim_dev is None:
            self._sim_dev = ModbusSimDevice(device_id=self.device_id)
            self._gateway.add_device(self._sim_dev)
        return self._sim_dev

    @property
    def uses_modbus(self) -> bool:
        return self._sim_dev is not None
