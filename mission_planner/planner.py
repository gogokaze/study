"""Async mission execution engine for YFL Robotics devices."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


@dataclass
class MissionRecord:
    mission_id: str
    device_id: str
    mission_name: str
    started_at: float
    status: str = "RUNNING"   # RUNNING | COMPLETE | CANCELLED | FAILED
    result: Any = None
    error: Optional[str] = None
    task: Optional[asyncio.Task] = field(default=None, compare=False, repr=False)


# A mission factory is a coroutine function that accepts (device) and returns any result.
MissionFactory = Callable[..., Coroutine[Any, Any, Any]]


class MissionPlanner:
    """
    Async mission scheduling engine.

    Usage::

        planner = MissionPlanner()
        planner.register_device("GT3-001", drone_instance)
        planner.register_mission("patrol", lambda dev: DronePatrolMission(waypoints).execute(dev))

        mission_id = await planner.execute_mission("GT3-001", "patrol")
        print(planner.get_active_missions())
        await planner.cancel_mission(mission_id)
    """

    def __init__(self) -> None:
        self._devices: dict[str, Any] = {}
        self._mission_factories: dict[str, MissionFactory] = {}
        self._records: dict[str, MissionRecord] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_device(self, device_id: str, device: Any) -> None:
        """Bind a device instance so missions can target it by ID."""
        self._devices[device_id] = device
        logger.debug("MissionPlanner: registered device %s", device_id)

    def register_mission(self, mission_name: str, factory: MissionFactory) -> None:
        """
        Register a named mission factory.

        *factory* is a callable that accepts a device instance and returns a coroutine,
        e.g. ``lambda dev: PatrolMission(waypoints).execute(dev)``.
        """
        self._mission_factories[mission_name] = factory
        logger.debug("MissionPlanner: registered mission '%s'", mission_name)

    def add_mission(self, mission_name: str, factory: MissionFactory) -> None:
        """Alias for register_mission for ergonomic compatibility."""
        self.register_mission(mission_name, factory)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_mission(self, device_id: str, mission_name: str) -> str:
        """
        Start *mission_name* on *device_id* asynchronously.

        Returns the *mission_id* which can be used to cancel or inspect the mission.
        Raises KeyError if device or mission name is unknown.
        """
        if device_id not in self._devices:
            raise KeyError(f"Unknown device: {device_id!r}")
        if mission_name not in self._mission_factories:
            raise KeyError(f"Unknown mission: {mission_name!r}")

        device = self._devices[device_id]
        factory = self._mission_factories[mission_name]
        mission_id = str(uuid.uuid4())[:8]

        record = MissionRecord(
            mission_id=mission_id,
            device_id=device_id,
            mission_name=mission_name,
            started_at=time.time(),
        )
        self._records[mission_id] = record

        async def _run() -> None:
            try:
                logger.info(
                    "Mission %s [%s] started on device %s",
                    mission_name, mission_id, device_id,
                )
                result = await factory(device)
                record.status = "COMPLETE"
                record.result = result
                logger.info("Mission %s [%s] completed", mission_name, mission_id)
            except asyncio.CancelledError:
                record.status = "CANCELLED"
                logger.info("Mission %s [%s] cancelled", mission_name, mission_id)
                raise
            except Exception as exc:
                record.status = "FAILED"
                record.error = str(exc)
                logger.exception("Mission %s [%s] failed: %s", mission_name, mission_id, exc)

        task = asyncio.create_task(_run(), name=f"mission-{mission_id}")
        record.task = task
        return mission_id

    async def cancel_mission(self, mission_id: str) -> bool:
        """
        Cancel a running mission by ID.

        Returns True if the mission was running and has been cancelled, False otherwise.
        """
        record = self._records.get(mission_id)
        if record is None:
            logger.warning("cancel_mission: unknown mission_id %s", mission_id)
            return False
        if record.task is None or record.task.done():
            return False
        record.task.cancel()
        try:
            await record.task
        except (asyncio.CancelledError, Exception):
            pass
        return True

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_active_missions(self) -> list[dict]:
        """Return a list of currently running mission records as dicts."""
        return [
            {
                "mission_id": r.mission_id,
                "device_id": r.device_id,
                "mission_name": r.mission_name,
                "started_at": r.started_at,
                "status": r.status,
                "error": r.error,
            }
            for r in self._records.values()
            if r.status == "RUNNING"
        ]

    def get_all_missions(self) -> list[dict]:
        """Return a list of all mission records (running + completed)."""
        return [
            {
                "mission_id": r.mission_id,
                "device_id": r.device_id,
                "mission_name": r.mission_name,
                "started_at": r.started_at,
                "status": r.status,
                "error": r.error,
            }
            for r in self._records.values()
        ]

    def get_mission_status(self, mission_id: str) -> Optional[dict]:
        """Return the status dict for a single mission, or None if not found."""
        r = self._records.get(mission_id)
        if r is None:
            return None
        return {
            "mission_id": r.mission_id,
            "device_id": r.device_id,
            "mission_name": r.mission_name,
            "started_at": r.started_at,
            "status": r.status,
            "result": r.result,
            "error": r.error,
        }
