import random
import time
from devices.base_device import BaseDevice
from telemetry_hub.schema import TelemetryPacket, IMUData, GPSData, DeviceStatus, DeviceType


class GT3Drone(BaseDevice):
    def __init__(self, device_id: str = "GT3-001") -> None:
        super().__init__(device_id, DeviceType.GT3_DRONE.value)
        self._battery = 100.0
        self._altitude = 0.0
        self._lat = 37.5665
        self._lon = 126.9780
        self._speed = 0.0
        self._yaw = 0.0
        self._pitch = 0.0
        self._roll = 0.0
        self._motor_pwm: list[float] = [1500.0] * 4
        self._rssi = -60

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
        self._battery = max(0.0, self._battery - random.uniform(0.01, 0.05))
        self._altitude += random.uniform(-0.5, 0.5)
        self._altitude = max(0.0, self._altitude)
        self._lat += random.uniform(-0.00005, 0.00005)
        self._lon += random.uniform(-0.00005, 0.00005)
        self._speed = max(0.0, self._speed + random.uniform(-0.5, 0.5))
        self._yaw = (self._yaw + random.uniform(-2.0, 2.0)) % 360
        self._pitch = max(-30.0, min(30.0, self._pitch + random.uniform(-1.0, 1.0)))
        self._roll = max(-30.0, min(30.0, self._roll + random.uniform(-1.0, 1.0)))
        self._motor_pwm = [1500.0 + random.uniform(-100, 100) for _ in range(4)]
        self._rssi = int(max(-90, min(-40, self._rssi + random.randint(-2, 2))))
        self.status = DeviceStatus.RUNNING

        return TelemetryPacket(
            device=self.device_id,
            device_type=self.device_type,
            timestamp=time.time(),
            battery=round(self._battery, 1),
            status=self.status.value,
            imu=IMUData(
                roll=round(self._roll, 2),
                pitch=round(self._pitch, 2),
                yaw=round(self._yaw, 2),
            ),
            gps=GPSData(
                lat=round(self._lat, 6),
                lon=round(self._lon, 6),
                alt=round(self._altitude, 1),
                fix=True,
            ),
            extra={
                "speed": round(self._speed, 2),
                "motor_pwm": [round(v, 1) for v in self._motor_pwm],
                "rssi": self._rssi,
            },
        )
