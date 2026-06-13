import random
import time
from devices.base_device import BaseDevice
from telemetry_hub.schema import TelemetryPacket, IMUData, DeviceStatus, DeviceType

_JOINT_NAMES = [
    "FL_hip", "FL_thigh", "FL_calf",
    "FR_hip", "FR_thigh", "FR_calf",
    "RL_hip", "RL_thigh", "RL_calf",
    "RR_hip", "RR_thigh", "RR_calf",
]


class Go2Dog(BaseDevice):
    def __init__(self, device_id: str = "Go2-001") -> None:
        super().__init__(device_id, DeviceType.UNITREE_GO2.value)
        self._battery = 100.0
        self._joint_positions = {j: 0.0 for j in _JOINT_NAMES}
        self._joint_torques = {j: 0.0 for j in _JOINT_NAMES}
        self._vx = self._vy = self._vz = 0.0
        self._lidar_ranges = [2.0] * 360

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
        self._battery = max(0.0, self._battery - random.uniform(0.01, 0.03))
        for j in _JOINT_NAMES:
            self._joint_positions[j] = round(random.uniform(-1.5, 1.5), 3)
            self._joint_torques[j] = round(random.uniform(-20.0, 20.0), 2)
        self._vx = round(random.uniform(-1.5, 1.5), 3)
        self._vy = round(random.uniform(-0.5, 0.5), 3)
        self._lidar_ranges = [round(max(0.1, 2.0 + random.uniform(-0.5, 0.5)), 2) for _ in range(360)]
        self.status = DeviceStatus.RUNNING

        return TelemetryPacket(
            device=self.device_id,
            device_type=self.device_type,
            timestamp=time.time(),
            battery=round(self._battery, 1),
            status=self.status.value,
            imu=IMUData(
                roll=round(random.uniform(-5, 5), 2),
                pitch=round(random.uniform(-5, 5), 2),
                yaw=round(random.uniform(0, 360), 2),
                ax=round(random.uniform(-0.5, 0.5), 3),
                ay=round(random.uniform(-0.5, 0.5), 3),
                az=round(9.81 + random.uniform(-0.1, 0.1), 3),
            ),
            extra={
                "joint_positions": self._joint_positions,
                "joint_torques": self._joint_torques,
                "velocity": {"vx": self._vx, "vy": self._vy, "vz": self._vz},
                "lidar_min": min(self._lidar_ranges),
                "lidar_max": max(self._lidar_ranges),
            },
        )
