from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from enum import Enum
import time
import json


class DeviceType(Enum):
    GT3_DRONE = "GT3"
    Z908_FPV = "Z908"
    UNITREE_GO2 = "Go2"
    ROBOT_ARM = "RobotArm"
    CNC_MACHINE = "CNC"
    SUBMARINE = "Submarine"


class DeviceStatus(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"
    CHARGING = "CHARGING"


@dataclass
class IMUData:
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    az: float = 0.0


@dataclass
class GPSData:
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0
    fix: bool = False


@dataclass
class TelemetryPacket:
    device: str
    device_type: str
    timestamp: float = field(default_factory=time.time)
    battery: Optional[float] = None
    status: str = DeviceStatus.IDLE.value
    imu: Optional[IMUData] = None
    gps: Optional[GPSData] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d)

    @classmethod
    def from_json(cls, data: str) -> "TelemetryPacket":
        d = json.loads(data)
        if d.get("imu"):
            d["imu"] = IMUData(**d["imu"])
        if d.get("gps"):
            d["gps"] = GPSData(**d["gps"])
        return cls(**d)
