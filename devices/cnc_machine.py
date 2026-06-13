import random
import time
from devices.base_device import BaseDevice
from telemetry_hub.schema import TelemetryPacket, DeviceStatus, DeviceType


class CNCMachine(BaseDevice):
    def __init__(self, device_id: str = "CNC-001") -> None:
        super().__init__(device_id, DeviceType.CNC_MACHINE.value)
        self._spindle_rpm = 0.0
        self._x = self._y = self._z = 0.0
        self._feed_rate = 0.0
        self._spindle_temp = 25.0
        self._spindle_current = 0.0
        self._vibration = 0.0

    def connect(self) -> bool:
        self._connected = True
        self.status = DeviceStatus.IDLE
        return True

    def disconnect(self) -> None:
        self._connected = False
        self.status = DeviceStatus.OFFLINE

    def get_telemetry(self) -> TelemetryPacket:
        return self.simulate()

    def simulate(self) -> TelemetryPacket:
        self._spindle_rpm = round(max(0.0, 12000 + random.uniform(-200, 200)), 0)
        self._x = round(self._x + random.uniform(-0.5, 0.5), 3)
        self._y = round(self._y + random.uniform(-0.5, 0.5), 3)
        self._z = round(max(-50.0, self._z + random.uniform(-0.2, 0.2)), 3)
        self._feed_rate = round(max(0.0, 1500 + random.uniform(-100, 100)), 1)
        self._spindle_temp = round(max(25.0, self._spindle_temp + random.uniform(-0.2, 0.5)), 1)
        self._spindle_current = round(max(0.0, 4.5 + random.uniform(-0.5, 0.5)), 2)
        self._vibration = round(max(0.0, random.uniform(0.01, 0.15)), 4)
        self.status = DeviceStatus.RUNNING

        return TelemetryPacket(
            device=self.device_id,
            device_type=self.device_type,
            timestamp=time.time(),
            status=self.status.value,
            extra={
                "spindle_rpm": self._spindle_rpm,
                "axis": {"x": self._x, "y": self._y, "z": self._z},
                "feed_rate": self._feed_rate,
                "spindle_temp": self._spindle_temp,
                "spindle_current": self._spindle_current,
                "vibration": self._vibration,
            },
        )
