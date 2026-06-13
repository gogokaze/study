"""Go2 warehouse patrol mission — tours patrol points and optionally scans QR codes."""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PatrolPoint:
    x: float          # metres from origin
    y: float
    label: str = ""   # descriptive label (e.g. "Shelf-A3")
    qr_scan: bool = False   # stop and attempt QR code scan here


@dataclass
class Go2WarehouseMission:
    """
    Drives the Go2 quadruped through a list of patrol points.

    If *qr_scan_enabled* is True, the robot pauses at points marked
    ``qr_scan=True`` and records a simulated scan result.
    """

    patrol_points: list[PatrolPoint] = field(default_factory=list)
    qr_scan_enabled: bool = True
    speed_mps: float = 0.8   # simulated walking speed

    @classmethod
    def from_coords(cls, coords: list[tuple[float, float, str]], **kwargs) -> "Go2WarehouseMission":
        """
        Build from a list of (x, y, label) tuples.  Every third point is
        automatically flagged for QR scanning.
        """
        points = [
            PatrolPoint(x=c[0], y=c[1], label=c[2], qr_scan=(i % 3 == 2))
            for i, c in enumerate(coords)
        ]
        return cls(patrol_points=points, **kwargs)

    async def execute(self, go2: Any) -> dict:
        """Execute the warehouse patrol on *go2* device instance."""
        device_id: str = getattr(go2, "device_id", "unknown")
        logger.info(
            "[%s] Go2WarehouseMission starting — %d points, QR scan: %s",
            device_id, len(self.patrol_points), self.qr_scan_enabled,
        )

        visited: list[dict] = []
        scan_results: list[dict] = []

        for idx, point in enumerate(self.patrol_points):
            logger.info(
                "[%s] Moving to patrol point %d/%d '%s' (%.1f, %.1f)",
                device_id, idx + 1, len(self.patrol_points),
                point.label, point.x, point.y,
            )
            # Simulate travel time based on distance (simplified)
            travel_time = max(0.2, abs(point.x + point.y) * 0.01)
            await asyncio.sleep(min(travel_time, 1.0))

            packet = go2.simulate()
            entry: dict = {
                "point_index": idx,
                "label": point.label,
                "x": point.x,
                "y": point.y,
                "battery": packet.battery,
                "status": packet.status,
                "qr_scanned": False,
                "qr_result": None,
            }

            if self.qr_scan_enabled and point.qr_scan:
                logger.info("[%s] QR scan at '%s'", device_id, point.label)
                await asyncio.sleep(0.3)
                # Simulated QR result
                qr_data = f"ITEM-{random.randint(1000, 9999)}-{point.label.replace(' ', '_')}"
                entry["qr_scanned"] = True
                entry["qr_result"] = qr_data
                scan_results.append({"label": point.label, "qr": qr_data})
                logger.info("[%s] QR scan result: %s", device_id, qr_data)

            visited.append(entry)

        logger.info("[%s] Go2WarehouseMission complete", device_id)
        return {
            "mission": "go2_warehouse",
            "device_id": device_id,
            "points_visited": len(visited),
            "qr_scans": scan_results,
            "log": visited,
        }
