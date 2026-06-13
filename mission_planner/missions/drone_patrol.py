"""Drone patrol mission — flies through a list of GPS waypoints."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Waypoint:
    lat: float
    lon: float
    alt: float          # metres AGL
    loiter_s: float = 2.0   # seconds to loiter at waypoint


@dataclass
class DronePatrolMission:
    """
    Flies the drone through each waypoint in order, loiters briefly,
    then returns to the origin.

    *execute(drone)* is an async coroutine that can be awaited directly or
    wrapped in a MissionPlanner factory.
    """

    waypoints: list[Waypoint] = field(default_factory=list)
    rtl_on_complete: bool = True   # Return-to-launch after last waypoint

    # ------------------------------------------------------------------
    # Convenience constructor
    # ------------------------------------------------------------------

    @classmethod
    def from_coords(cls, coords: list[tuple[float, float, float]], **kwargs) -> "DronePatrolMission":
        """
        Build a DronePatrolMission from a list of (lat, lon, alt) tuples.

        Example::

            mission = DronePatrolMission.from_coords([
                (37.5665, 126.9780, 50),
                (37.5670, 126.9785, 50),
                (37.5675, 126.9780, 30),
            ])
        """
        waypoints = [Waypoint(lat=c[0], lon=c[1], alt=c[2]) for c in coords]
        return cls(waypoints=waypoints, **kwargs)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, drone: Any) -> dict:
        """
        Execute the patrol mission on *drone*.

        The drone object is expected to have a ``simulate()`` method (for
        simulation) and a ``device_id`` attribute.  In production, replace
        the simulate calls with actual flight-controller commands.

        Returns a summary dict when complete.
        """
        device_id: str = getattr(drone, "device_id", "unknown")
        logger.info(
            "[%s] DronePatrolMission starting — %d waypoints, RTL=%s",
            device_id, len(self.waypoints), self.rtl_on_complete,
        )

        visited: list[dict] = []

        for idx, wp in enumerate(self.waypoints):
            logger.info(
                "[%s] Navigating to waypoint %d/%d — lat=%.6f lon=%.6f alt=%.1fm",
                device_id, idx + 1, len(self.waypoints), wp.lat, wp.lon, wp.alt,
            )
            # Simulate travel time proportional to step (0.5-1 s per WP in sim)
            await asyncio.sleep(0.5)

            # Capture a telemetry snapshot
            packet = drone.simulate()
            visited.append({
                "waypoint_index": idx,
                "lat": wp.lat,
                "lon": wp.lon,
                "alt": wp.alt,
                "battery_on_arrival": packet.battery,
                "status": packet.status,
            })

            if wp.loiter_s > 0:
                logger.debug("[%s] Loitering at WP %d for %.1fs", device_id, idx, wp.loiter_s)
                await asyncio.sleep(wp.loiter_s)

        if self.rtl_on_complete:
            logger.info("[%s] RTL — returning to launch", device_id)
            await asyncio.sleep(0.5)

        logger.info("[%s] DronePatrolMission complete", device_id)
        return {
            "mission": "drone_patrol",
            "device_id": device_id,
            "waypoints_visited": len(visited),
            "log": visited,
        }
