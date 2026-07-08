"""Ratsnest generation: unrouted airwires between same-net pads."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import List

from pcb_design.components import ComponentInstance


@dataclass(frozen=True)
class RatsnestLine:
    net: str
    ref_a: str
    pad_a: str
    x1: float
    y1: float
    ref_b: str
    pad_b: str
    x2: float
    y2: float

    @property
    def length_mm(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    def to_dict(self) -> dict:
        return {
            "net": self.net,
            "ref_a": self.ref_a,
            "pad_a": self.pad_a,
            "x1": self.x1,
            "y1": self.y1,
            "ref_b": self.ref_b,
            "pad_b": self.pad_b,
            "x2": self.x2,
            "y2": self.y2,
            "length_mm": self.length_mm,
        }


def build_ratsnest(components: List[ComponentInstance]) -> List[RatsnestLine]:
    """Groups pads by net and connects them with a nearest-neighbor chain
    (a cheap stand-in for a true minimum spanning tree, good enough for
    ratsnest visualization purposes)."""
    nets: dict = defaultdict(list)
    for comp in components:
        for pad_name, net, x, y in comp.pad_world_positions():
            if net == "GND":
                continue  # ground handled by plane, not ratsnest
            nets[net].append((comp.ref, pad_name, x, y))

    lines: List[RatsnestLine] = []
    for net, pads in nets.items():
        if len(pads) < 2:
            continue
        remaining = pads[1:]
        chain = [pads[0]]
        while remaining:
            last = chain[-1]
            nearest_idx = min(
                range(len(remaining)),
                key=lambda i: math.hypot(remaining[i][2] - last[2], remaining[i][3] - last[3]),
            )
            nearest = remaining.pop(nearest_idx)
            lines.append(
                RatsnestLine(
                    net=net,
                    ref_a=last[0],
                    pad_a=last[1],
                    x1=last[2],
                    y1=last[3],
                    ref_b=nearest[0],
                    pad_b=nearest[1],
                    x2=nearest[2],
                    y2=nearest[3],
                )
            )
            chain.append(nearest)

    return lines
