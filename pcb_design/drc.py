"""DRC engine: manufacturing rule checks + sensor noise isolation checks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from pcb_design.board import BoardSpec
from pcb_design.components import ComponentCategory, ComponentInstance
from pcb_design.design_rules import DesignRules, IsolationRules
from pcb_design.net_classes import NetClass


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class DrcViolation:
    rule: str
    severity: Severity
    message: str
    refs: List[str]
    x_mm: Optional[float] = None
    y_mm: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "refs": self.refs,
            "x_mm": self.x_mm,
            "y_mm": self.y_mm,
        }


def _bbox_distance(a, b) -> float:
    """Edge-to-edge distance between two axis-aligned bboxes (0 if overlapping)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(bx0 - ax1, ax0 - bx1, 0.0)
    dy = max(by0 - ay1, ay0 - by1, 0.0)
    return math.hypot(dx, dy)


def _bbox_overlaps(a, b) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def check_board_bounds(
    components: List[ComponentInstance], board: BoardSpec
) -> List[DrcViolation]:
    violations = []
    for comp in components:
        x0, y0, x1, y1 = comp.courtyard_bbox()
        if x0 < 0 or y0 < 0 or x1 > board.width_mm or y1 > board.height_mm:
            violations.append(
                DrcViolation(
                    rule="board_outline",
                    severity=Severity.ERROR,
                    message=f"{comp.ref} courtyard extends outside board outline",
                    refs=[comp.ref],
                    x_mm=comp.x_mm,
                    y_mm=comp.y_mm,
                )
            )
    return violations


def check_courtyard_overlap(components: List[ComponentInstance]) -> List[DrcViolation]:
    violations = []
    for i, a in enumerate(components):
        for b in components[i + 1:]:
            if _bbox_overlaps(a.courtyard_bbox(), b.courtyard_bbox()):
                violations.append(
                    DrcViolation(
                        rule="courtyard_overlap",
                        severity=Severity.ERROR,
                        message=f"{a.ref} and {b.ref} courtyards overlap",
                        refs=[a.ref, b.ref],
                        x_mm=(a.x_mm + b.x_mm) / 2.0,
                        y_mm=(a.y_mm + b.y_mm) / 2.0,
                    )
                )
    return violations


def check_isolation(
    components: List[ComponentInstance],
    rules: IsolationRules = None,
) -> List[DrcViolation]:
    """IMU/MAG-to-regulator keep-away, and any sensor-to-power-pad clearance."""
    rules = rules or IsolationRules()
    violations: List[DrcViolation] = []

    by_category = {}
    for comp in components:
        by_category.setdefault(comp.category, []).append(comp)

    regulators = by_category.get(ComponentCategory.REGULATOR, [])
    imus = by_category.get(ComponentCategory.SENSOR_IMU, [])
    mags = by_category.get(ComponentCategory.SENSOR_MAG, [])
    sensors = imus + mags + by_category.get(ComponentCategory.SENSOR_BARO, [])

    def center_distance(a: ComponentInstance, b: ComponentInstance) -> float:
        return math.hypot(a.x_mm - b.x_mm, a.y_mm - b.y_mm)

    for imu in imus:
        for reg in regulators:
            dist = center_distance(imu, reg)
            if dist < rules.imu_to_regulator_mm:
                violations.append(
                    DrcViolation(
                        rule="imu_isolation",
                        severity=Severity.ERROR,
                        message=(
                            f"{imu.ref} (IMU) is {dist:.1f}mm from {reg.ref} (regulator); "
                            f"requires >= {rules.imu_to_regulator_mm}mm"
                        ),
                        refs=[imu.ref, reg.ref],
                        x_mm=imu.x_mm,
                        y_mm=imu.y_mm,
                    )
                )

    for mag in mags:
        for reg in regulators:
            dist = center_distance(mag, reg)
            if dist < rules.mag_to_regulator_mm:
                violations.append(
                    DrcViolation(
                        rule="mag_isolation",
                        severity=Severity.ERROR,
                        message=(
                            f"{mag.ref} (MAG) is {dist:.1f}mm from {reg.ref} (regulator); "
                            f"requires >= {rules.mag_to_regulator_mm}mm"
                        ),
                        refs=[mag.ref, reg.ref],
                        x_mm=mag.x_mm,
                        y_mm=mag.y_mm,
                    )
                )

    power_nets = {"VBAT", "3V3"}
    for sensor in sensors:
        for comp in components:
            if comp is sensor:
                continue
            for pad_name, net, px, py in comp.pad_world_positions():
                if net not in power_nets:
                    continue
                dist = math.hypot(sensor.x_mm - px, sensor.y_mm - py)
                if dist < rules.sensor_to_power_mm:
                    violations.append(
                        DrcViolation(
                            rule="sensor_power_clearance",
                            severity=Severity.WARNING,
                            message=(
                                f"{sensor.ref} sensor is {dist:.1f}mm from {comp.ref}.{pad_name} "
                                f"({net}); requires >= {rules.sensor_to_power_mm}mm"
                            ),
                            refs=[sensor.ref, comp.ref],
                            x_mm=sensor.x_mm,
                            y_mm=sensor.y_mm,
                        )
                    )

    return violations


def check_net_class_widths(
    routes: List[dict], net_classes: dict
) -> List[DrcViolation]:
    """routes: [{"net": str, "net_class": str, "width_mm": float}, ...]"""
    violations = []
    for route in routes:
        net_class: Optional[NetClass] = net_classes.get(route.get("net_class"))
        if net_class is None:
            continue
        width = route.get("width_mm", 0.0)
        if width < net_class.min_trace_width_mm:
            violations.append(
                DrcViolation(
                    rule="net_class_width",
                    severity=Severity.ERROR,
                    message=(
                        f"Net {route.get('net')} routed at {width}mm, below "
                        f"{net_class.name} class minimum {net_class.min_trace_width_mm}mm"
                    ),
                    refs=[route.get("net", "")],
                )
            )
    return violations


def run_drc(
    components: List[ComponentInstance],
    board: BoardSpec,
    isolation_rules: IsolationRules = None,
    net_classes: dict = None,
    routes: List[dict] = None,
) -> dict:
    violations: List[DrcViolation] = []
    violations += check_board_bounds(components, board)
    violations += check_courtyard_overlap(components)
    violations += check_isolation(components, isolation_rules)
    if routes and net_classes:
        violations += check_net_class_widths(routes, net_classes)

    errors = [v for v in violations if v.severity == Severity.ERROR]
    warnings = [v for v in violations if v.severity == Severity.WARNING]

    return {
        "passed": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "violations": [v.to_dict() for v in violations],
    }
