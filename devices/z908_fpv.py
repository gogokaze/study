import random
import time
from devices.base_device import BaseDevice
from telemetry_hub.schema import TelemetryPacket, DeviceStatus, DeviceType


class Z908FPV(BaseDevice):
    def __init__(self, device_id: str = "Z908-001", video_stream_url: str = "") -> None:
        super().__init__(device_id, DeviceType.Z908_FPV.value)
        self._battery = 100.0
        self._rssi = -55
        self._altitude = 0.0
        self.video_stream_url = video_stream_url

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
        self._battery = max(0.0, self._battery - random.uniform(0.02, 0.08))
        self._rssi = int(max(-90, min(-40, self._rssi + random.randint(-3, 3))))
        self._altitude = max(0.0, self._altitude + random.uniform(-1.0, 1.0))
        self.status = DeviceStatus.RUNNING

        return TelemetryPacket(
            device=self.device_id,
            device_type=self.device_type,
            timestamp=time.time(),
            battery=round(self._battery, 1),
            status=self.status.value,
            extra={
                "rssi": self._rssi,
                "altitude": round(self._altitude, 1),
                "video_stream": self.video_stream_url,
            },
        )
