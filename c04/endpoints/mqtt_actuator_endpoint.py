# endpoints/mqtt_actuator_endpoint.py · 加热器命令通道 · MQTT 信道插件 · 一类两用
from __future__ import annotations

import json
import logging
import queue
import time
from typing import Any

from core.base_endpoint import BaseActuatorEndpoint, Role
from core.registry import register

log = logging.getLogger(__name__)
_CMD_QUEUE_MAX = 64


@register("MqttActuatorEndpoint")
class MqttActuatorEndpoint(BaseActuatorEndpoint):
    def __init__(
        self, name: str = "heater_ep", *, role: Role = "server",
        broker_host: str = "127.0.0.1", broker_port: int = 1883,
        topic: str | None = None, qos: int = 0,
        client_id: str | None = None, keepalive: int = 60,
    ) -> None:
        super().__init__(name, role)
        self._broker_host = broker_host
        self._broker_port = int(broker_port)
        self._topic = topic or f"my-station/actuator/{name}/cmd"
        self._qos = int(qos)
        self._client_id = client_id
        self._keepalive = int(keepalive)
        self._client: Any = None
        self._cmd_q: queue.Queue[float] = queue.Queue(maxsize=_CMD_QUEUE_MAX)

    def bind(self, ctx) -> None:
        """client 端照 ctx 坐标连 broker；server 端默认连本机 broker。"""
        if self.role == "client":
            self._broker_host = ctx.host
            self._broker_port = ctx.port

    def start(self) -> None:
        client = self._build_client()
        client.on_connect = self._on_connect
        if self.role == "server":
            client.on_message = self._on_message
        client.connect_async(self._broker_host, self._broker_port, keepalive=self._keepalive)
        client.loop_start()
        self._client = client
        self._running = True

    def stop(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
                self._client.loop_stop()
            except Exception:
                pass
            self._client = None
        self._running = False

    def poll_command(self) -> float | None:
        self._check_role("server", "poll_command")
        latest: float | None = None
        while True:
            try:
                latest = self._cmd_q.get_nowait()
            except queue.Empty:
                break
        return latest

    def write(self, value: float) -> None:
        self._check_role("client", "write")
        if self._client is None:
            return
        # 原样发，保留类型：bool 开关命令不能被强转成 1.0/0.0。
        payload = json.dumps({"ts": int(time.time() * 1000), "value": value})
        try:
            self._client.publish(self._topic, payload, qos=self._qos)
        except Exception as e:
            log.debug("publish error: %s", e)

    def _build_client(self) -> Any:
        import paho.mqtt.client as mqtt

        kwargs: dict[str, Any] = {}
        if hasattr(mqtt, "CallbackAPIVersion"):
            kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION2
        if self._client_id:
            kwargs["client_id"] = self._client_id
        return mqtt.Client(**kwargs)

    def _on_connect(self, client, userdata, flags, reason_code, *args) -> None:
        if self.role == "server":
            client.subscribe(self._topic, qos=self._qos)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            data = json.loads(msg.payload)
        except (json.JSONDecodeError, ValueError, AttributeError):
            return
        v = data.get("value") if isinstance(data, dict) else None
        # bool 是 int 的子类，这里显式允许 bool/int/float，拒掉 None 和字符串。
        if not isinstance(v, (bool, int, float)):
            return
        try:
            self._cmd_q.put_nowait(v)
        except queue.Full:
            try:
                self._cmd_q.get_nowait()
            except queue.Empty:
                pass
            self._cmd_q.put_nowait(v)
