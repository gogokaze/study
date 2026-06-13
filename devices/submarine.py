import random
import time
from devices.base_device import BaseDevice
from telemetry_hub.schema import TelemetryPacket, DeviceStatus, DeviceType


class LegoSubmarine(BaseDevice):
    def __init__(self, device_id: str = "SUB-001") -> None:
        super().__init__(device_id, DeviceType.SUBMARINE.value)
        self._battery = 100.0
        self._depth = 0.0
        self._water_temp = 20.0
        self._heading = 0.0
        self._motor_left = 0
        self._motor_right = 0
        self._leak_detected = False

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
        self._battery = max(0.0, self._battery - random.uniform(0.005, 0.02))
        self._depth = round(max(0.0, self._depth + random.uniform(-0.1, 0.1)), 2)
        self._water_temp = round(self._water_temp + random.uniform(-0.05, 0.05), 2)
        self._heading = round((self._heading + random.uniform(-1.0, 1.0)) % 360, 1)
        self._motor_left = int(max(-255, min(255, self._motor_left + random.randint(-10, 10))))
        self._motor_right = int(max(-255, min(255, self._motor_right + random.randint(-10, 10))))
        self._leak_detected = random.random() < 0.001
        self.status = DeviceStatus.ERROR if self._leak_detected else DeviceStatus.RUNNING

        return TelemetryPacket(
            device=self.device_id,
            device_type=self.device_type,
            timestamp=time.time(),
            battery=round(self._battery, 1),
            status=self.status.value,
            extra={
                "depth": self._depth,
                "water_temp": self._water_temp,
                "heading": self._heading,
                "motor_left": self._motor_left,
                "motor_right": self._motor_right,
                "leak_detected": self._leak_detected,
            },
        )
