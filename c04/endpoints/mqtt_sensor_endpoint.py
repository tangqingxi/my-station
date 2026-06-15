# endpoints/mqtt_sensor_endpoint.py · 温度通道 · MQTT 信道插件 · 一类两用
from __future__ import annotations

import json
import logging
import time
from typing import Any

from core.base_endpoint import BaseSensorEndpoint, Role
from core.registry import register

log = logging.getLogger(__name__)


@register("MqttSensorEndpoint")
class MqttSensorEndpoint(BaseSensorEndpoint):
    def __init__(
        self, name: str = "temp_ep", *, role: Role = "server",
        broker_host: str = "127.0.0.1", broker_port: int = 1883,
        topic: str | None = None, qos: int = 0,
        client_id: str | None = None, keepalive: int = 60,
    ) -> None:
        super().__init__(name, role)
        self._broker_host = broker_host
        self._broker_port = int(broker_port)
        self._topic = topic or f"my-station/sensor/{name}"
        self._qos = int(qos)
        self._client_id = client_id
        self._keepalive = int(keepalive)
        self._client: Any = None
        self._latest_value: float | None = None

    def bind(self, ctx) -> None:
        """client 端照 ctx 坐标连 broker；server 端默认连本机 broker。"""
        if self.role == "client":
            self._broker_host = ctx.host
            self._broker_port = ctx.port

    def start(self) -> None:
        client = self._build_client()
        client.on_connect = self._on_connect
        if self.role == "client":
            client.on_message = self._on_message
            self._latest_value = None
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

    def update(self, value: float) -> None:
        self._check_role("server", "update")
        if self._client is None:
            return
        payload = json.dumps({"ts": int(time.time() * 1000), "value": float(value)})
        try:
            self._client.publish(self._topic, payload, qos=self._qos)
        except Exception as e:
            log.debug("publish error: %s", e)

    def read(self) -> float:
        self._check_role("client", "read")
        v = self._latest_value
        if v is None:
            raise IOError(f"MqttSensorEndpoint {self.name!r} 还未收到第一条温度值")
        return v

    def _build_client(self) -> Any:
        import paho.mqtt.client as mqtt

        kwargs: dict[str, Any] = {}
        if hasattr(mqtt, "CallbackAPIVersion"):
            kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION2
        if self._client_id:
            kwargs["client_id"] = self._client_id
        return mqtt.Client(**kwargs)

    def _on_connect(self, client, userdata, flags, reason_code, *args) -> None:
        if self.role == "client":
            self._latest_value = None
            client.subscribe(self._topic, qos=self._qos)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            data = json.loads(msg.payload)
        except (json.JSONDecodeError, ValueError, AttributeError):
            return
        v = data.get("value") if isinstance(data, dict) else None
        if v is None:
            return
        try:
            self._latest_value = float(v)
        except (TypeError, ValueError):
            pass
