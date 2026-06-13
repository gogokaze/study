"""Tests for TelemetryHub — register, publish, subscribe."""

import asyncio
import pytest
import pytest_asyncio

from telemetry_hub.hub import TelemetryHub
from telemetry_hub.schema import TelemetryPacket, DeviceType, DeviceStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test_hub.db")


@pytest.fixture
def hub(tmp_db):
    return TelemetryHub(db_path=tmp_db)


def make_packet(device: str = "GT3-001", device_type: str = "GT3", battery: float = 90.0) -> TelemetryPacket:
    return TelemetryPacket(
        device=device,
        device_type=device_type,
        battery=battery,
        status=DeviceStatus.RUNNING.value,
    )


# ---------------------------------------------------------------------------
# Device registration
# ---------------------------------------------------------------------------

class TestRegisterDevice:
    def test_registers_single_device(self, hub: TelemetryHub) -> None:
        hub.register_device("GT3-001", "GT3")
        status = hub.get_status_all()
        assert "GT3-001" in status

    def test_register_is_idempotent(self, hub: TelemetryHub) -> None:
        hub.register_device("GT3-001", "GT3")
        hub.register_device("GT3-001", "GT3")   # duplicate — should not raise
        status = hub.get_status_all()
        assert len([k for k in status if k == "GT3-001"]) == 1

    def test_multiple_devices_registered(self, hub: TelemetryHub) -> None:
        for did in ["GT3-001", "Go2-001", "ARM-001"]:
            hub.register_device(did, did.split("-")[0])
        status = hub.get_status_all()
        assert len(status) == 3

    def test_registered_device_has_metadata(self, hub: TelemetryHub) -> None:
        hub.register_device("GT3-001", "GT3", metadata={"firmware": "v2.3"})
        status = hub.get_status_all()
        assert status["GT3-001"]["firmware"] == "v2.3"


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

class TestPublish:
    @pytest.mark.asyncio
    async def test_publish_auto_registers_device(self, hub: TelemetryHub) -> None:
        await hub.start()
        packet = make_packet("NEW-001", "GT3")
        await hub.publish(packet)
        assert "NEW-001" in hub.get_status_all()
        await hub.stop()

    @pytest.mark.asyncio
    async def test_publish_updates_latest(self, hub: TelemetryHub) -> None:
        await hub.start()
        hub.register_device("GT3-001", "GT3")
        pkt = make_packet("GT3-001", "GT3", battery=77.5)
        await hub.publish(pkt)
        latest = hub.get_latest_packet("GT3-001")
        assert latest is not None
        assert latest.battery == pytest.approx(77.5)
        await hub.stop()

    @pytest.mark.asyncio
    async def test_publish_multiple_packets_keeps_latest(self, hub: TelemetryHub) -> None:
        await hub.start()
        hub.register_device("GT3-001", "GT3")
        for battery in [90.0, 80.0, 70.0]:
            await hub.publish(make_packet("GT3-001", "GT3", battery=battery))
        latest = hub.get_latest_packet("GT3-001")
        assert latest.battery == pytest.approx(70.0)
        await hub.stop()

    @pytest.mark.asyncio
    async def test_publish_persists_to_db(self, hub: TelemetryHub) -> None:
        await hub.start()
        await hub.publish(make_packet("GT3-001", "GT3", battery=55.0))
        row = hub._db.get_latest("GT3-001")
        assert row is not None
        assert row["battery"] == pytest.approx(55.0)
        await hub.stop()


# ---------------------------------------------------------------------------
# Subscribe
# ---------------------------------------------------------------------------

class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscriber_called_on_publish(self, hub: TelemetryHub) -> None:
        received: list[TelemetryPacket] = []

        async def cb(p: TelemetryPacket) -> None:
            received.append(p)

        await hub.start()
        hub.subscribe("GT3", cb)
        await hub.publish(make_packet("GT3-001", "GT3"))
        assert len(received) == 1
        assert received[0].device == "GT3-001"
        await hub.stop()

    @pytest.mark.asyncio
    async def test_subscriber_not_called_for_different_type(self, hub: TelemetryHub) -> None:
        received: list[TelemetryPacket] = []

        async def cb(p: TelemetryPacket) -> None:
            received.append(p)

        await hub.start()
        hub.subscribe("GT3", cb)
        await hub.publish(make_packet("Go2-001", "Go2"))   # different type
        assert len(received) == 0
        await hub.stop()

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_called(self, hub: TelemetryHub) -> None:
        calls: list[str] = []

        async def cb1(p: TelemetryPacket) -> None:
            calls.append("cb1")

        async def cb2(p: TelemetryPacket) -> None:
            calls.append("cb2")

        await hub.start()
        hub.subscribe("GT3", cb1)
        hub.subscribe("GT3", cb2)
        await hub.publish(make_packet("GT3-001", "GT3"))
        assert "cb1" in calls
        assert "cb2" in calls
        await hub.stop()

    @pytest.mark.asyncio
    async def test_subscribe_with_enum_value(self, hub: TelemetryHub) -> None:
        received: list[TelemetryPacket] = []

        async def cb(p: TelemetryPacket) -> None:
            received.append(p)

        await hub.start()
        hub.subscribe(DeviceType.GT3_DRONE, cb)
        await hub.publish(make_packet("GT3-001", DeviceType.GT3_DRONE.value))
        assert len(received) == 1
        await hub.stop()


# ---------------------------------------------------------------------------
# get_status_all
# ---------------------------------------------------------------------------

class TestGetStatusAll:
    @pytest.mark.asyncio
    async def test_returns_all_registered_devices(self, hub: TelemetryHub) -> None:
        await hub.start()
        hub.register_device("GT3-001", "GT3")
        hub.register_device("Go2-001", "Go2")
        status = hub.get_status_all()
        assert "GT3-001" in status
        assert "Go2-001" in status
        await hub.stop()

    @pytest.mark.asyncio
    async def test_latest_none_before_publish(self, hub: TelemetryHub) -> None:
        await hub.start()
        hub.register_device("GT3-001", "GT3")
        status = hub.get_status_all()
        assert status["GT3-001"]["latest"] is None
        await hub.stop()

    @pytest.mark.asyncio
    async def test_latest_populated_after_publish(self, hub: TelemetryHub) -> None:
        await hub.start()
        hub.register_device("GT3-001", "GT3")
        await hub.publish(make_packet("GT3-001", "GT3", battery=42.0))
        status = hub.get_status_all()
        assert status["GT3-001"]["latest"]["battery"] == pytest.approx(42.0)
        await hub.stop()
