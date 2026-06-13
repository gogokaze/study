from abc import ABC, abstractmethod
from telemetry_hub.schema import TelemetryPacket, DeviceStatus


class BaseDevice(ABC):
    def __init__(self, device_id: str, device_type: str) -> None:
        self.device_id = device_id
        self.device_type = device_type
        self.status = DeviceStatus.OFFLINE
        self._connected = False

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def get_telemetry(self) -> TelemetryPacket: ...

    @abstractmethod
    def simulate(self) -> TelemetryPacket: ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.device_id}, status={self.status.value})"
