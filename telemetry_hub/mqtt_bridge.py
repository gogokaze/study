"""MQTT ↔ TelemetryHub bridge using paho-mqtt."""

import json
import logging
import threading
from typing import Callable, Optional

try:
    import paho.mqtt.client as mqtt
    _PAHO_AVAILABLE = True
except ImportError:
    _PAHO_AVAILABLE = False

from telemetry_hub.schema import TelemetryPacket, DeviceType

logger = logging.getLogger(__name__)

TOPIC_TEMPLATE = "yfl/{device_type}/telemetry"


def _topic_for(device_type: str) -> str:
    return TOPIC_TEMPLATE.format(device_type=device_type)


def _device_type_from_topic(topic: str) -> Optional[str]:
    """Extract device_type string from `yfl/<device_type>/telemetry`."""
    parts = topic.split("/")
    if len(parts) == 3 and parts[0] == "yfl" and parts[2] == "telemetry":
        return parts[1]
    return None


class MQTTBridge:
    """
    Bidirectional bridge between the MQTT broker and internal Python callbacks.

    Usage::

        bridge = MQTTBridge(host="localhost", port=1883)
        bridge.subscribe(DeviceType.GT3_DRONE.value, my_callback)
        bridge.start()
        bridge.publish(packet)
        bridge.stop()

    The *subscribe* callbacks receive a :class:`TelemetryPacket` decoded from
    the JSON payload that arrived on the MQTT topic.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        client_id: str = "yfl_telemetry_hub",
        keepalive: int = 60,
    ) -> None:
        if not _PAHO_AVAILABLE:
            raise RuntimeError(
                "paho-mqtt is not installed. Run: pip install paho-mqtt"
            )
        self._host = host
        self._port = port
        self._keepalive = keepalive
        self._client = mqtt.Client(client_id=client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        # device_type_value -> list[callback(TelemetryPacket)]
        self._handlers: dict[str, list[Callable[[TelemetryPacket], None]]] = {}
        self._connected = threading.Event()
        self._stopped = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Connect to the broker and start the background network loop."""
        self._client.connect(self._host, self._port, self._keepalive)
        self._client.loop_start()
        if not self._connected.wait(timeout=10):
            raise TimeoutError(f"Could not connect to MQTT broker at {self._host}:{self._port}")
        # Subscribe to all YFL telemetry topics
        self._client.subscribe("yfl/+/telemetry", qos=1)
        logger.info("MQTTBridge connected to %s:%s", self._host, self._port)

    def stop(self) -> None:
        """Disconnect and stop the network loop."""
        self._stopped = True
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTTBridge disconnected")

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish(self, packet: TelemetryPacket) -> None:
        """Publish *packet* to the appropriate MQTT topic."""
        if not self._connected.is_set():
            logger.warning("MQTTBridge not connected — dropping packet for %s", packet.device)
            return
        topic = _topic_for(packet.device_type)
        payload = packet.to_json()
        result = self._client.publish(topic, payload, qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error("MQTT publish failed (rc=%s) for topic %s", result.rc, topic)

    # ------------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------------

    def subscribe(
        self,
        device_type: str,
        callback: Callable[[TelemetryPacket], None],
    ) -> None:
        """Register *callback* for inbound packets of *device_type*."""
        if isinstance(device_type, DeviceType):
            device_type = device_type.value
        self._handlers.setdefault(device_type, []).append(callback)

    def unsubscribe(self, device_type: str, callback: Callable[[TelemetryPacket], None]) -> None:
        if isinstance(device_type, DeviceType):
            device_type = device_type.value
        handlers = self._handlers.get(device_type, [])
        try:
            handlers.remove(callback)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # paho callbacks
    # ------------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc: int) -> None:
        if rc == 0:
            self._connected.set()
            logger.info("MQTT broker connection established (rc=0)")
        else:
            logger.error("MQTT broker refused connection (rc=%s)", rc)

    def _on_disconnect(self, client, userdata, rc: int) -> None:
        self._connected.clear()
        if not self._stopped:
            logger.warning("MQTT disconnected (rc=%s), paho will auto-reconnect", rc)

    def _on_message(self, client, userdata, msg: "mqtt.MQTTMessage") -> None:
        device_type = _device_type_from_topic(msg.topic)
        if device_type is None:
            return
        try:
            packet = TelemetryPacket.from_json(msg.payload.decode("utf-8"))
        except Exception:
            logger.exception("Failed to decode MQTT message on %s", msg.topic)
            return

        handlers = self._handlers.get(device_type, [])
        for cb in handlers:
            try:
                cb(packet)
            except Exception:
                logger.exception("MQTT handler raised for device_type=%s", device_type)
