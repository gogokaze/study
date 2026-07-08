"""Tests for the GoJokaze MK.1 PCB design module."""

import pytest

from pcb_design.board import BoardSpec
from pcb_design.components import (
    ComponentCategory,
    ComponentInstance,
    FP_LGA_IMU,
    FP_SOT23_5_BUCK,
    default_layout,
)
from pcb_design.design_rules import DEFAULT_ISOLATION_RULES, DesignRules
from pcb_design.drc import (
    check_courtyard_overlap,
    check_isolation,
    check_net_class_widths,
    run_drc,
)
from pcb_design.net_classes import DEFAULT_NET_CLASSES, classify_net
from pcb_design.ratsnest import build_ratsnest
from pcb_design.stackup import DEFAULT_STACKUP, LayerFunction


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

def test_board_dimensions():
    board = BoardSpec()
    assert board.width_mm == 36.0
    assert board.height_mm == 36.0


def test_mount_holes_on_pattern():
    board = BoardSpec()
    holes = board.mount_holes()
    assert len(holes) == 4
    cx, cy = board.width_mm / 2.0, board.height_mm / 2.0
    for h in holes:
        dist_from_center = ((h.x - cx) ** 2 + (h.y - cy) ** 2) ** 0.5
        assert dist_from_center == pytest.approx(board.mount_hole_pattern_mm / (2 ** 0.5), abs=0.01)


def test_board_contains():
    board = BoardSpec()
    assert board.contains(18, 18)
    assert not board.contains(-1, 18)
    assert not board.contains(18, 40)


# ---------------------------------------------------------------------------
# Stackup
# ---------------------------------------------------------------------------

def test_stackup_is_four_layer_signal_gnd_power_signal():
    assert len(DEFAULT_STACKUP) == 4
    functions = [layer.function for layer in DEFAULT_STACKUP]
    assert functions == [
        LayerFunction.SIGNAL,
        LayerFunction.GROUND_PLANE,
        LayerFunction.POWER_PLANE,
        LayerFunction.SIGNAL,
    ]


# ---------------------------------------------------------------------------
# Net classes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "net_name,expected_class",
    [
        ("SPI1_SCK", "SPI"),
        ("I2C1_SCL", "I2C"),
        ("USART1_TX", "UART"),
        ("PWM_M1", "PWM"),
        ("3V3", "3V3"),
        ("VBAT", "VBAT"),
    ],
)
def test_classify_net(net_name, expected_class):
    assert classify_net(net_name) == expected_class


def test_vbat_is_widest_net_class():
    widths = {name: nc.trace_width_mm for name, nc in DEFAULT_NET_CLASSES.items()}
    assert widths["VBAT"] == max(widths.values())


# ---------------------------------------------------------------------------
# Design rules
# ---------------------------------------------------------------------------

def test_default_design_rules_match_common_fab_capability():
    rules = DesignRules()
    assert rules.min_trace_width_mm == 0.15
    assert rules.min_spacing_mm == 0.15
    assert rules.min_via_diameter_mm == 0.30
    assert rules.board_thickness_mm == 1.6
    assert rules.surface_finish == "ENIG"


def test_isolation_rules_defaults():
    rules = DEFAULT_ISOLATION_RULES
    assert rules.imu_to_regulator_mm == 12.0
    assert rules.mag_to_regulator_mm == 12.0
    assert rules.sensor_to_power_mm == 10.0


# ---------------------------------------------------------------------------
# Default layout / DRC
# ---------------------------------------------------------------------------

def test_default_layout_passes_drc():
    board = BoardSpec()
    components = default_layout()
    result = run_drc(
        components,
        board,
        isolation_rules=DEFAULT_ISOLATION_RULES,
        net_classes=DEFAULT_NET_CLASSES,
    )
    assert result["passed"] is True
    assert result["error_count"] == 0


def test_default_layout_has_no_courtyard_overlaps():
    components = default_layout()
    assert check_courtyard_overlap(components) == []


def test_imu_too_close_to_regulator_triggers_violation():
    imu = ComponentInstance("U2", FP_LGA_IMU, ComponentCategory.SENSOR_IMU, 10.0, 10.0)
    reg = ComponentInstance("U4", FP_SOT23_5_BUCK, ComponentCategory.REGULATOR, 5.0, 5.0)
    violations = check_isolation([imu, reg], DEFAULT_ISOLATION_RULES)
    rules_hit = {v.rule for v in violations}
    assert "imu_isolation" in rules_hit


def test_imu_far_from_regulator_has_no_isolation_violation():
    imu = ComponentInstance("U2", FP_LGA_IMU, ComponentCategory.SENSOR_IMU, 30.0, 5.0)
    reg = ComponentInstance("U4", FP_SOT23_5_BUCK, ComponentCategory.REGULATOR, 5.0, 5.0)
    violations = check_isolation([imu, reg], DEFAULT_ISOLATION_RULES)
    assert violations == []


def test_courtyard_overlap_detected():
    imu_a = ComponentInstance("U2", FP_LGA_IMU, ComponentCategory.SENSOR_IMU, 10.0, 10.0)
    imu_b = ComponentInstance("U5", FP_LGA_IMU, ComponentCategory.SENSOR_IMU, 10.5, 10.0)
    violations = check_courtyard_overlap([imu_a, imu_b])
    assert len(violations) == 1
    assert violations[0].rule == "courtyard_overlap"


def test_net_class_width_below_minimum_flagged():
    routes = [{"net": "VBAT_IN", "net_class": "VBAT", "width_mm": 0.3}]
    violations = check_net_class_widths(routes, DEFAULT_NET_CLASSES)
    assert len(violations) == 1
    assert violations[0].rule == "net_class_width"


def test_net_class_width_meeting_minimum_not_flagged():
    routes = [{"net": "VBAT_IN", "net_class": "VBAT", "width_mm": 0.8}]
    violations = check_net_class_widths(routes, DEFAULT_NET_CLASSES)
    assert violations == []


# ---------------------------------------------------------------------------
# Ratsnest
# ---------------------------------------------------------------------------

def test_ratsnest_connects_every_multi_pad_net():
    components = default_layout()
    lines = build_ratsnest(components)
    assert len(lines) > 0
    for line in lines:
        assert line.length_mm > 0
        assert line.net != "GND"  # ground handled by plane, excluded from ratsnest


def test_ratsnest_excludes_ground_net():
    components = default_layout()
    lines = build_ratsnest(components)
    nets = {line.net for line in lines}
    assert "GND" not in nets
