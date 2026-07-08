"""Footprint / component placement model and the default GoJokaze MK.1 layout."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


class ComponentCategory(str, Enum):
    MCU = "mcu"
    SENSOR_IMU = "sensor_imu"
    SENSOR_MAG = "sensor_mag"
    SENSOR_BARO = "sensor_baro"
    REGULATOR = "regulator"
    CONNECTOR = "connector"
    PASSIVE = "passive"


@dataclass(frozen=True)
class Pad:
    name: str
    dx_mm: float  # offset from footprint origin
    dy_mm: float
    net: str


@dataclass(frozen=True)
class Footprint:
    name: str
    width_mm: float
    height_mm: float
    courtyard_margin_mm: float
    pads: Tuple[Pad, ...] = field(default_factory=tuple)


@dataclass
class ComponentInstance:
    ref: str
    footprint: Footprint
    category: ComponentCategory
    x_mm: float
    y_mm: float
    rotation_deg: float = 0.0
    layer: str = "L1 TOP"

    def courtyard_bbox(self) -> Tuple[float, float, float, float]:
        """Axis-aligned bbox (min_x, min_y, max_x, max_y), ignoring rotation."""
        half_w = self.footprint.width_mm / 2.0 + self.footprint.courtyard_margin_mm
        half_h = self.footprint.height_mm / 2.0 + self.footprint.courtyard_margin_mm
        return (
            self.x_mm - half_w,
            self.y_mm - half_h,
            self.x_mm + half_w,
            self.y_mm + half_h,
        )

    def pad_world_positions(self) -> List[Tuple[str, str, float, float]]:
        """Returns [(pad_name, net, world_x, world_y), ...]."""
        return [
            (pad.name, pad.net, self.x_mm + pad.dx_mm, self.y_mm + pad.dy_mm)
            for pad in self.footprint.pads
        ]

    def to_dict(self) -> dict:
        return {
            "ref": self.ref,
            "footprint": self.footprint.name,
            "category": self.category.value,
            "x_mm": self.x_mm,
            "y_mm": self.y_mm,
            "rotation_deg": self.rotation_deg,
            "layer": self.layer,
            "width_mm": self.footprint.width_mm,
            "height_mm": self.footprint.height_mm,
            "courtyard_bbox": self.courtyard_bbox(),
            "pads": [
                {"name": name, "net": net, "x_mm": x, "y_mm": y}
                for name, net, x, y in self.pad_world_positions()
            ],
        }


# ---------------------------------------------------------------------------
# Footprint library
# ---------------------------------------------------------------------------

FP_QFN_100 = Footprint(
    "LQFP-100_STM32F427",
    14.0,
    14.0,
    1.0,
    pads=(
        Pad("SPI1_SCK", -7.0, 2.0, "SPI1_SCK"),
        Pad("SPI1_MISO", -7.0, 3.0, "SPI1_MISO"),
        Pad("SPI1_MOSI", -7.0, 4.0, "SPI1_MOSI"),
        Pad("I2C1_SCL", 7.0, 2.0, "I2C1_SCL"),
        Pad("I2C1_SDA", 7.0, 3.0, "I2C1_SDA"),
        Pad("USART1_TX", 7.0, -2.0, "USART1_TX"),
        Pad("USART1_RX", 7.0, -3.0, "USART1_RX"),
        Pad("VDD_3V3", 0.0, -7.0, "3V3"),
        Pad("VSS", 0.0, 7.0, "GND"),
        Pad("PWM1", -7.0, -2.0, "PWM_M1"),
        Pad("PWM2", -7.0, -3.0, "PWM_M2"),
    ),
)

FP_LGA_IMU = Footprint(
    "LGA-16_ICM42688",
    3.0,
    3.0,
    1.5,
    pads=(
        Pad("SCK", -1.5, 0.5, "SPI1_SCK"),
        Pad("MISO", -1.5, -0.5, "SPI1_MISO"),
        Pad("MOSI", 1.5, 0.5, "SPI1_MOSI"),
        Pad("CS", 1.5, -0.5, "IMU_CS"),
        Pad("VDD", 0.0, 1.5, "3V3"),
        Pad("GND", 0.0, -1.5, "GND"),
    ),
)

FP_QFN_MAG = Footprint(
    "QFN-16_QMC5883",
    3.0,
    3.0,
    1.5,
    pads=(
        Pad("SCL", -1.5, 0.5, "I2C1_SCL"),
        Pad("SDA", -1.5, -0.5, "I2C1_SDA"),
        Pad("VDD", 0.0, 1.5, "3V3"),
        Pad("GND", 0.0, -1.5, "GND"),
    ),
)

FP_SOT23_5_BUCK = Footprint(
    "SOT23-5_BuckRegulator",
    3.0,
    3.0,
    1.0,
    pads=(
        Pad("VIN", -1.5, 0.0, "VBAT"),
        Pad("VOUT", 1.5, 0.0, "3V3"),
        Pad("GND", 0.0, -1.5, "GND"),
    ),
)

FP_JST_GH_4P = Footprint(
    "JST-GH-4P",
    6.0,
    4.0,
    0.5,
    pads=(
        Pad("VBAT", -2.0, 0.0, "VBAT"),
        Pad("GND", -0.7, 0.0, "GND"),
        Pad("TX", 0.7, 0.0, "USART1_TX"),
        Pad("RX", 2.0, 0.0, "USART1_RX"),
    ),
)

FP_JST_SH_4P = Footprint(
    "JST-SH-4P_ESC",
    5.0,
    3.0,
    0.5,
    pads=(
        Pad("M1", -1.5, 0.0, "PWM_M1"),
        Pad("M2", -0.5, 0.0, "PWM_M2"),
        Pad("M3", 0.5, 0.0, "PWM_M3"),
        Pad("M4", 1.5, 0.0, "PWM_M4"),
    ),
)


def default_layout() -> List[ComponentInstance]:
    """GoJokaze MK.1 default placement on the 36x36mm board.

    Regulator sits near the VBAT input corner; IMU and MAG are pushed to the
    opposite side of the board to satisfy the >=12mm isolation keep-away from
    the buck regulator, and >=10mm from any power net pad.
    """
    return [
        ComponentInstance("U1", FP_QFN_100, ComponentCategory.MCU, 18.0, 18.0),
        ComponentInstance("U2", FP_LGA_IMU, ComponentCategory.SENSOR_IMU, 31.0, 5.0),
        ComponentInstance("U3", FP_QFN_MAG, ComponentCategory.SENSOR_MAG, 31.0, 31.0),
        ComponentInstance("U4", FP_SOT23_5_BUCK, ComponentCategory.REGULATOR, 5.0, 5.0),
        ComponentInstance("J1", FP_JST_GH_4P, ComponentCategory.CONNECTOR, 4.0, 18.0, rotation_deg=90),
        ComponentInstance("J2", FP_JST_SH_4P, ComponentCategory.CONNECTOR, 18.0, 33.0),
    ]
