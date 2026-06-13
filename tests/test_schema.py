"""Tests for TelemetryPacket serialization and deserialization."""

import json
import time
import pytest

from telemetry_hub.schema import (
    TelemetryPacket,
    IMUData,
    GPSData,
    DeviceType,
    DeviceStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_full_packet() -> TelemetryPacket:
    return TelemetryPacket(
        device="GT3-001",
        device_type=DeviceType.GT3_DRONE.value,
        timestamp=1_700_000_000.0,
        battery=87.3,
        status=DeviceStatus.RUNNING.value,
        imu=IMUData(roll=1.1, pitch=2.2, yaw=90.0, ax=0.01, ay=0.02, az=9.81),
        gps=GPSData(lat=37.5665, lon=126.9780, alt=50.0, fix=True),
        extra={"speed": 12.5, "rssi": -65},
    )


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestTelemetryPacketToJson:
    def test_returns_valid_json_string(self) -> None:
        packet = make_full_packet()
        result = packet.to_json()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_device_field_preserved(self) -> None:
        packet = make_full_packet()
        parsed = json.loads(packet.to_json())
        assert parsed["device"] == "GT3-001"

    def test_device_type_field_preserved(self) -> None:
        packet = make_full_packet()
        parsed = json.loads(packet.to_json())
        assert parsed["device_type"] == DeviceType.GT3_DRONE.value

    def test_battery_field_preserved(self) -> None:
        packet = make_full_packet()
        parsed = json.loads(packet.to_json())
        assert abs(parsed["battery"] - 87.3) < 1e-6

    def test_status_field_preserved(self) -> None:
        packet = make_full_packet()
        parsed = json.loads(packet.to_json())
        assert parsed["status"] == DeviceStatus.RUNNING.value

    def test_imu_nested_dict_present(self) -> None:
        packet = make_full_packet()
        parsed = json.loads(packet.to_json())
        assert "imu" in parsed
        assert parsed["imu"]["roll"] == pytest.approx(1.1)
        assert parsed["imu"]["az"] == pytest.approx(9.81)

    def test_gps_nested_dict_present(self) -> None:
        packet = make_full_packet()
        parsed = json.loads(packet.to_json())
        assert "gps" in parsed
        assert parsed["gps"]["lat"] == pytest.approx(37.5665)
        assert parsed["gps"]["fix"] is True

    def test_extra_dict_preserved(self) -> None:
        packet = make_full_packet()
        parsed = json.loads(packet.to_json())
        assert parsed["extra"]["speed"] == pytest.approx(12.5)
        assert parsed["extra"]["rssi"] == -65

    def test_null_imu_serialises_as_none(self) -> None:
        packet = TelemetryPacket(device="CNC-001", device_type="CNC")
        parsed = json.loads(packet.to_json())
        assert parsed["imu"] is None

    def test_null_gps_serialises_as_none(self) -> None:
        packet = TelemetryPacket(device="CNC-001", device_type="CNC")
        parsed = json.loads(packet.to_json())
        assert parsed["gps"] is None


# ---------------------------------------------------------------------------
# Deserialisation
# ---------------------------------------------------------------------------

class TestTelemetryPacketFromJson:
    def test_roundtrip_minimal(self) -> None:
        original = TelemetryPacket(device="ARM-001", device_type="RobotArm")
        restored = TelemetryPacket.from_json(original.to_json())
        assert restored.device == original.device
        assert restored.device_type == original.device_type

    def test_roundtrip_full_packet(self) -> None:
        original = make_full_packet()
        restored = TelemetryPacket.from_json(original.to_json())
        assert restored.device == original.device
        assert restored.battery == pytest.approx(original.battery)
        assert restored.status == original.status

    def test_imu_restored_as_imudata(self) -> None:
        original = make_full_packet()
        restored = TelemetryPacket.from_json(original.to_json())
        assert isinstance(restored.imu, IMUData)
        assert restored.imu.roll == pytest.approx(original.imu.roll)
        assert restored.imu.az == pytest.approx(original.imu.az)

    def test_gps_restored_as_gpsdata(self) -> None:
        original = make_full_packet()
        restored = TelemetryPacket.from_json(original.to_json())
        assert isinstance(restored.gps, GPSData)
        assert restored.gps.lat == pytest.approx(original.gps.lat)
        assert restored.gps.fix is True

    def test_extra_dict_roundtrip(self) -> None:
        original = make_full_packet()
        restored = TelemetryPacket.from_json(original.to_json())
        assert restored.extra["rssi"] == original.extra["rssi"]

    def test_from_json_with_no_imu_gps(self) -> None:
        raw = json.dumps({
            "device": "SUB-001",
            "device_type": "Submarine",
            "timestamp": time.time(),
            "battery": 45.0,
            "status": "RUNNING",
            "imu": None,
            "gps": None,
            "extra": {"depth": 1.5},
        })
        packet = TelemetryPacket.from_json(raw)
        assert packet.device == "SUB-001"
        assert packet.imu is None
        assert packet.gps is None
        assert packet.extra["depth"] == pytest.approx(1.5)

    def test_timestamp_preserved(self) -> None:
        ts = 1_700_000_001.123
        packet = TelemetryPacket(device="X", device_type="GT3", timestamp=ts)
        restored = TelemetryPacket.from_json(packet.to_json())
        assert restored.timestamp == pytest.approx(ts)


# ---------------------------------------------------------------------------
# IMUData / GPSData standalone
# ---------------------------------------------------------------------------

class TestIMUData:
    def test_defaults(self) -> None:
        imu = IMUData()
        assert imu.roll == 0.0
        assert imu.az == 0.0

    def test_custom_values(self) -> None:
        imu = IMUData(roll=10.0, pitch=-5.0, yaw=180.0, ax=0.1, ay=0.2, az=9.8)
        assert imu.yaw == pytest.approx(180.0)


class TestGPSData:
    def test_defaults(self) -> None:
        gps = GPSData()
        assert gps.fix is False

    def test_fix_true(self) -> None:
        gps = GPSData(lat=37.0, lon=127.0, alt=100.0, fix=True)
        assert gps.fix is True
