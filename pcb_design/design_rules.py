"""Manufacturing design rules aligned with common JLCPCB/PCBWay capability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignRules:
    min_trace_width_mm: float = 0.15
    min_spacing_mm: float = 0.15
    min_via_diameter_mm: float = 0.30
    min_via_drill_mm: float = 0.20
    board_thickness_mm: float = 1.6
    surface_finish: str = "ENIG"

    def to_dict(self) -> dict:
        return {
            "min_trace_width_mm": self.min_trace_width_mm,
            "min_spacing_mm": self.min_spacing_mm,
            "min_via_diameter_mm": self.min_via_diameter_mm,
            "min_via_drill_mm": self.min_via_drill_mm,
            "board_thickness_mm": self.board_thickness_mm,
            "surface_finish": self.surface_finish,
        }


DEFAULT_DESIGN_RULES = DesignRules()


@dataclass(frozen=True)
class IsolationRules:
    """Minimum keep-away distances for sensor noise isolation."""

    imu_to_regulator_mm: float = 12.0
    mag_to_regulator_mm: float = 12.0
    sensor_to_power_mm: float = 10.0

    def to_dict(self) -> dict:
        return {
            "imu_to_regulator_mm": self.imu_to_regulator_mm,
            "mag_to_regulator_mm": self.mag_to_regulator_mm,
            "sensor_to_power_mm": self.sensor_to_power_mm,
        }


DEFAULT_ISOLATION_RULES = IsolationRules()
