"""4-layer stackup: TOP signal / GND plane / POWER plane / BOTTOM signal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class LayerFunction(str, Enum):
    SIGNAL = "signal"
    GROUND_PLANE = "ground_plane"
    POWER_PLANE = "power_plane"


@dataclass(frozen=True)
class Layer:
    index: int
    name: str
    function: LayerFunction
    thickness_mm: float


DEFAULT_STACKUP: List[Layer] = [
    Layer(1, "L1 TOP", LayerFunction.SIGNAL, 0.035),
    Layer(2, "L2 GND", LayerFunction.GROUND_PLANE, 0.035),
    Layer(3, "L3 POWER", LayerFunction.POWER_PLANE, 0.035),
    Layer(4, "L4 BOTTOM", LayerFunction.SIGNAL, 0.035),
]


def stackup_to_dict(layers: List[Layer] = None) -> dict:
    layers = layers if layers is not None else DEFAULT_STACKUP
    return {
        "layer_count": len(layers),
        "layers": [
            {
                "index": layer.index,
                "name": layer.name,
                "function": layer.function.value,
                "thickness_mm": layer.thickness_mm,
            }
            for layer in layers
        ],
        "benefits": [
            "IMU noise reduction via adjacent ground plane",
            "Stable return current path",
            "Reduced EMI radiation",
        ],
    }
