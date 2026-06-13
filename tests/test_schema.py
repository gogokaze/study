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


def _make_packet(**kwargs) -> TelemetryPacket:
    defaults = dict(
        device="test-001",
        device_type=DeviceType.GT3_DRONE.value,
        battery=85.0,
        status=DeviceStatus.RUNNING.value,
    )
    defaults.update(kwargs)
    return TelemetryPacket(**defaults)


class TestTelemetryPacketBasic:
    def test_default_timestamp(self) -> None:
        before = time.time()
        pkt = _make_packet()
        after = time.time()
        assert before <= pkt.timestamp <= after

    def test_fields(self) -> None:
        pkt = _make_packet(battery=72.5)
        assert pkt.device == "test-001"
        assert pkt.battery == 72.5
        assert pkt.status == DeviceStatus.RUNNING.value

    def test_extra_default_empty(self) -> None:
        pkt = _make_packet()
        assert pkt.extra == {}


class TestTelemetryPacketSerialization:
    def test_to_json_is_valid_json(self) -> None:
        pkt = _make_packet()
        raw = pkt.to_json()
        parsed = json.loads(raw)
        assert parsed["device"] == "test-001"

    def test_roundtrip_no_imu_gps(self) -> None:
        pkt = _make_packet(battery=50.0)
        restored = TelemetryPacket.from_json(pkt.to_json())
        assert restored.device == pkt.device
        assert restored.battery == pkt.battery
        assert restored.imu is None
        assert restored.gps is None

    def test_roundtrip_with_imu(self) -> None:
        imu = IMUData(roll=1.5, pitch=-2.3, yaw=90.0, ax=0.1, ay=0.2, az=9.8)
        pkt = _make_packet(imu=imu)
        restored = TelemetryPacket.from_json(pkt.to_json())
        assert restored.imu is not None
        assert restored.imu.roll == pytest.approx(1.5)
        assert restored.imu.yaw == pytest.approx(90.0)

    def test_roundtrip_with_gps(self) -> None:
        gps = GPSData(lat=37.5665, lon=126.9780, alt=50.0, fix=True)
        pkt = _make_packet(gps=gps)
        restored = TelemetryPacket.from_json(pkt.to_json())
        assert restored.gps is not None
        assert restored.gps.lat == pytest.approx(37.5665)
        assert restored.gps.fix is True

    def test_roundtrip_with_extra(self) -> None:
        pkt = _make_packet(extra={"speed": 3.5, "motor_pwm": [1500, 1520, 1480, 1510]})
        restored = TelemetryPacket.from_json(pkt.to_json())
        assert restored.extra["speed"] == pytest.approx(3.5)
        assert len(restored.extra["motor_pwm"]) == 4

    def test_roundtrip_full(self) -> None:
        pkt = _make_packet(
            imu=IMUData(roll=2.0, pitch=-1.0, yaw=45.0),
            gps=GPSData(lat=37.0, lon=127.0, alt=100.0, fix=True),
            extra={"rssi": -65},
        )
        restored = TelemetryPacket.from_json(pkt.to_json())
        assert restored.imu.yaw == pytest.approx(45.0)
        assert restored.gps.fix is True
        assert restored.extra["rssi"] == -65


class TestDeviceTypeEnum:
    def test_all_values_unique(self) -> None:
        values = [dt.value for dt in DeviceType]
        assert len(values) == len(set(values))

    def test_expected_members(self) -> None:
        names = {dt.name for dt in DeviceType}
        assert "GT3_DRONE" in names
        assert "SUBMARINE" in names
