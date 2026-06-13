import random
import time
from devices.base_device import BaseDevice
from telemetry_hub.schema import TelemetryPacket, DeviceStatus, DeviceType

_TASK_STATES = ["IDLE", "PICK", "PLACE", "INSPECT", "SCAN_QR", "HOME"]


class RobotArm(BaseDevice):
    def __init__(self, device_id: str = "ARM-001") -> None:
        super().__init__(device_id, DeviceType.ROBOT_ARM.value)
        self._joint_angles = [0.0] * 6
        self._joint_currents = [0.0] * 6
        self._end_effector = {"x": 0.0, "y": 0.0, "z": 300.0, "rx": 0.0, "ry": 0.0, "rz": 0.0}
        self._temperatures = [25.0] * 6
        self._task_state = "IDLE"

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
        self._joint_angles = [round(a + random.uniform(-2.0, 2.0), 2) for a in self._joint_angles]
        self._joint_currents = [round(max(0, random.uniform(0.1, 2.5)), 3) for _ in range(6)]
        self._temperatures = [round(max(20.0, t + random.uniform(-0.1, 0.2)), 1) for t in self._temperatures]
        for k in self._end_effector:
            self._end_effector[k] = round(self._end_effector[k] + random.uniform(-1.0, 1.0), 2)
        self._task_state = random.choice(_TASK_STATES)
        self.status = DeviceStatus.RUNNING

        return TelemetryPacket(
            device=self.device_id,
            device_type=self.device_type,
            timestamp=time.time(),
            status=self.status.value,
            extra={
                "joint_angles": self._joint_angles,
                "joint_currents": self._joint_currents,
                "end_effector": self._end_effector,
                "temperatures": self._temperatures,
                "task_state": self._task_state,
            },
        )
