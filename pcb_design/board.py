"""Board outline and mechanical spec for GoJokaze MK.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class MountHole:
    x: float
    y: float
    diameter_mm: float = 3.2  # M3 clearance


@dataclass(frozen=True)
class BoardSpec:
    """36x36mm flight-controller board, M3 mount holes on a 30.5mm pattern."""

    width_mm: float = 36.0
    height_mm: float = 36.0
    mount_hole_pattern_mm: float = 30.5
    mount_hole_count: int = 4

    def mount_holes(self) -> List[MountHole]:
        offset = self.mount_hole_pattern_mm / 2.0
        cx, cy = self.width_mm / 2.0, self.height_mm / 2.0
        return [
            MountHole(cx - offset, cy - offset),
            MountHole(cx + offset, cy - offset),
            MountHole(cx - offset, cy + offset),
            MountHole(cx + offset, cy + offset),
        ]

    def outline(self) -> List[Tuple[float, float]]:
        return [
            (0.0, 0.0),
            (self.width_mm, 0.0),
            (self.width_mm, self.height_mm),
            (0.0, self.height_mm),
        ]

    def contains(self, x: float, y: float, margin_mm: float = 0.0) -> bool:
        return (
            margin_mm <= x <= self.width_mm - margin_mm
            and margin_mm <= y <= self.height_mm - margin_mm
        )

    def to_dict(self) -> dict:
        return {
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "mount_hole_pattern_mm": self.mount_hole_pattern_mm,
            "outline": self.outline(),
            "mount_holes": [
                {"x": h.x, "y": h.y, "diameter_mm": h.diameter_mm}
                for h in self.mount_holes()
            ],
        }
