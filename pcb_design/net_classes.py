"""Net class trace-width rules for common flight-controller signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class NetClass:
    name: str
    trace_width_mm: float
    min_trace_width_mm: float
    description: str


DEFAULT_NET_CLASSES: Dict[str, NetClass] = {
    "SPI": NetClass("SPI", 0.20, 0.15, "IMU/flash SPI bus"),
    "I2C": NetClass("I2C", 0.20, 0.15, "Mag/baro I2C bus"),
    "UART": NetClass("UART", 0.20, 0.15, "GPS/telemetry/ESC UARTs"),
    "PWM": NetClass("PWM", 0.25, 0.20, "Motor/servo PWM outputs"),
    "3V3": NetClass("3V3", 0.40, 0.30, "3.3V regulated rail"),
    "VBAT": NetClass("VBAT", 0.80, 0.60, "Battery power input"),
}


def classify_net(net_name: str) -> str:
    """Best-effort classification of a net name to one of DEFAULT_NET_CLASSES."""
    upper = net_name.upper()
    if "VBAT" in upper or "VBATT" in upper:
        return "VBAT"
    if "3V3" in upper or "3.3V" in upper:
        return "3V3"
    if "SPI" in upper:
        return "SPI"
    if "I2C" in upper or "SCL" in upper or "SDA" in upper:
        return "I2C"
    if "UART" in upper or "TX" in upper or "RX" in upper:
        return "UART"
    if "PWM" in upper or "MOTOR" in upper:
        return "PWM"
    return "UART"


def net_classes_to_dict() -> dict:
    return {
        name: {
            "trace_width_mm": nc.trace_width_mm,
            "min_trace_width_mm": nc.min_trace_width_mm,
            "description": nc.description,
        }
        for name, nc in DEFAULT_NET_CLASSES.items()
    }
