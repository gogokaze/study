"""Central async telemetry hub using asyncio queues."""

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Awaitable, Optional

from telemetry_hub.schema import TelemetryPacket, DeviceType
from telemetry_hub.database import TelemetryDatabase

logger = logging.getLogger(__name__)

# Callback type: async function that receives a TelemetryPacket
Callback = Callable[[TelemetryPacket], Awaitable[None]]


class TelemetryHub:
    """
    Central telemetry router.

    Devices publish packets here; subscribers receive them filtered by
    device_type.  All packets are persisted to SQLite via TelemetryDatabase.
    """

    def __init__(self, db_path: str = "yfl_telemetry.db") -> None:
        self._db = TelemetryDatabase(db_path)
        # device_id -> device metadata dict
        self._devices: dict[str, dict] = {}
        # device_type_value -> list of async callbacks
        self._subscribers: dict[str, list[Callback]] = defaultdict(list)
        # device_id -> asyncio.Queue[TelemetryPacket]
        self._queues: dict[str, asyncio.Queue[TelemetryPacket]] = {}
        # Latest packet per device
        self._latest: dict[str, TelemetryPacket] = {}
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Device registry
    # ------------------------------------------------------------------

    def register_device(self, device_id: str, device_type: str, metadata: Optional[dict] = None) -> None:
        """Register a device with the hub.  Idempotent."""
        if device_id not in self._devices:
            self._devices[device_id] = {
                "device_id": device_id,
                "device_type": device_type,
                **(metadata or {}),
            }
            self._queues[device_id] = asyncio.Queue(maxsize=256)
            logger.info("Registered device %s (%s)", device_id, device_type)

    # ------------------------------------------------------------------
    # Publish / Subscribe
    # ------------------------------------------------------------------

    async def publish(self, packet: TelemetryPacket) -> None:
        """Accept a telemetry packet, persist it, and fan-out to subscribers."""
        # Auto-register if first time seen
        if packet.device not in self._devices:
            self.register_device(packet.device, packet.device_type)

        self._latest[packet.device] = packet

        # Persist
        try:
            self._db.insert_packet(packet)
        except Exception:
            logger.exception("DB insert failed for %s", packet.device)

        # Notify subscribers
        callbacks = self._subscribers.get(packet.device_type, [])
        for cb in callbacks:
            try:
                await cb(packet)
            except Exception:
                logger.exception("Subscriber callback raised for %s", packet.device)

        # Also push into per-device queue (non-blocking drop if full)
        q = self._queues.get(packet.device)
        if q is not None:
            try:
                q.put_nowait(packet)
            except asyncio.QueueFull:
                # Drop oldest and enqueue newest
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                q.put_nowait(packet)

    def subscribe(self, device_type: str, callback: Callback) -> None:
        """
        Register *callback* to be called whenever a packet from *device_type*
        is published.  *device_type* should be a DeviceType.value string or
        a DeviceType enum member.
        """
        if isinstance(device_type, DeviceType):
            device_type = device_type.value
        self._subscribers[device_type].append(callback)
        logger.debug("New subscriber for device_type=%s", device_type)

    def unsubscribe(self, device_type: str, callback: Callback) -> None:
        """Remove a previously registered callback."""
        if isinstance(device_type, DeviceType):
            device_type = device_type.value
        try:
            self._subscribers[device_type].remove(callback)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status_all(self) -> dict[str, dict]:
        """
        Return a snapshot of all registered devices with their latest packet.
        Keys are device_ids; values are dicts with device metadata + latest telemetry.
        """
        result: dict[str, dict] = {}
        for device_id, meta in self._devices.items():
            latest = self._latest.get(device_id)
            entry = dict(meta)
            if latest is not None:
                entry["latest"] = {
                    "timestamp": latest.timestamp,
                    "battery": latest.battery,
                    "status": latest.status,
                    "extra": latest.extra,
                }
            else:
                entry["latest"] = None
            result[device_id] = entry
        return result

    def get_latest_packet(self, device_id: str) -> Optional[TelemetryPacket]:
        """Return the most recently published packet for *device_id*."""
        return self._latest.get(device_id)

    async def get_next_packet(self, device_id: str, timeout: float = 5.0) -> Optional[TelemetryPacket]:
        """Await the next packet from the per-device queue."""
        q = self._queues.get(device_id)
        if q is None:
            return None
        try:
            return await asyncio.wait_for(q.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._running = True
        logger.info("TelemetryHub started")

    async def stop(self) -> None:
        self._running = False
        self._db.close()
        logger.info("TelemetryHub stopped")
