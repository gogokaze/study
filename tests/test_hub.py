import asyncio
import pytest
from telemetry_hub.hub import TelemetryHub
from telemetry_hub.schema import TelemetryPacket, DeviceType, DeviceStatus


def _packet(device: str = "test-001", device_type: str = DeviceType.GT3_DRONE.value, battery: float = 80.0) -> TelemetryPacket:
    return TelemetryPacket(
        device=device,
        device_type=device_type,
        battery=battery,
        status=DeviceStatus.RUNNING.value,
    )


@pytest.fixture
def hub(tmp_path) -> TelemetryHub:
    return TelemetryHub(db_path=str(tmp_path / "test.db"))


class TestRegisterDevice:
    def test_register_appears_in_status(self, hub: TelemetryHub) -> None:
        hub.register_device("arm-001", DeviceType.ROBOT_ARM.value)
        status = hub.get_status_all()
        assert "arm-001" in status

    def test_register_idempotent(self, hub: TelemetryHub) -> None:
        hub.register_device("arm-001", DeviceType.ROBOT_ARM.value)
        hub.register_device("arm-001", DeviceType.ROBOT_ARM.value)
        assert len(hub.get_status_all()) == 1

    def test_multiple_devices(self, hub: TelemetryHub) -> None:
        hub.register_device("d1", DeviceType.GT3_DRONE.value)
        hub.register_device("d2", DeviceType.SUBMARINE.value)
        assert len(hub.get_status_all()) == 2


class TestPublish:
    def test_publish_auto_registers(self, hub: TelemetryHub) -> None:
        asyncio.run(hub.publish(_packet("drone-x")))
        assert "drone-x" in hub.get_status_all()

    def test_latest_packet_updated(self, hub: TelemetryHub) -> None:
        pkt = _packet(battery=55.5)
        asyncio.run(hub.publish(pkt))
        latest = hub.get_latest_packet("test-001")
        assert latest is not None
        assert latest.battery == pytest.approx(55.5)

    def test_multiple_publishes_keeps_latest(self, hub: TelemetryHub) -> None:
        asyncio.run(hub.publish(_packet(battery=90.0)))
        asyncio.run(hub.publish(_packet(battery=45.0)))
        latest = hub.get_latest_packet("test-001")
        assert latest.battery == pytest.approx(45.0)


class TestSubscribe:
    def test_subscriber_called_on_publish(self, hub: TelemetryHub) -> None:
        received: list[TelemetryPacket] = []

        async def cb(pkt: TelemetryPacket) -> None:
            received.append(pkt)

        hub.subscribe(DeviceType.GT3_DRONE.value, cb)

        async def run():
            await hub.publish(_packet())

        asyncio.run(run())
        assert len(received) == 1
        assert received[0].device == "test-001"

    def test_subscriber_not_called_for_other_type(self, hub: TelemetryHub) -> None:
        received: list[TelemetryPacket] = []

        async def cb(pkt: TelemetryPacket) -> None:
            received.append(pkt)

        hub.subscribe(DeviceType.SUBMARINE.value, cb)
        asyncio.run(hub.publish(_packet(device_type=DeviceType.GT3_DRONE.value)))
        assert len(received) == 0

    def test_unsubscribe(self, hub: TelemetryHub) -> None:
        received: list[TelemetryPacket] = []

        async def cb(pkt: TelemetryPacket) -> None:
            received.append(pkt)

        hub.subscribe(DeviceType.GT3_DRONE.value, cb)
        hub.unsubscribe(DeviceType.GT3_DRONE.value, cb)
        asyncio.run(hub.publish(_packet()))
        assert len(received) == 0

    def test_subscribe_with_enum(self, hub: TelemetryHub) -> None:
        received: list[TelemetryPacket] = []

        async def cb(pkt: TelemetryPacket) -> None:
            received.append(pkt)

        hub.subscribe(DeviceType.GT3_DRONE, cb)
        asyncio.run(hub.publish(_packet()))
        assert len(received) == 1


class TestGetStatusAll:
    def test_returns_dict(self, hub: TelemetryHub) -> None:
        assert isinstance(hub.get_status_all(), dict)

    def test_latest_none_before_publish(self, hub: TelemetryHub) -> None:
        hub.register_device("d1", DeviceType.GT3_DRONE.value)
        assert hub.get_status_all()["d1"]["latest"] is None

    def test_latest_populated_after_publish(self, hub: TelemetryHub) -> None:
        asyncio.run(hub.publish(_packet(battery=77.0)))
        assert hub.get_status_all()["test-001"]["latest"]["battery"] == pytest.approx(77.0)
