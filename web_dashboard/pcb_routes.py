"""FastAPI router exposing the GoJokaze MK.1 PCB design endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pcb_design.board import BoardSpec
from pcb_design.components import ComponentInstance, default_layout
from pcb_design.design_rules import DEFAULT_DESIGN_RULES, DEFAULT_ISOLATION_RULES
from pcb_design.drc import run_drc
from pcb_design.net_classes import DEFAULT_NET_CLASSES, net_classes_to_dict
from pcb_design.ratsnest import build_ratsnest
from pcb_design.stackup import stackup_to_dict

router = APIRouter(prefix="/api/pcb")

_board = BoardSpec()
_components: List[ComponentInstance] = default_layout()


class PositionUpdate(BaseModel):
    x_mm: float
    y_mm: float
    rotation_deg: float = 0.0


def _find_component(ref: str) -> ComponentInstance:
    for comp in _components:
        if comp.ref == ref:
            return comp
    raise HTTPException(status_code=404, detail=f"Component '{ref}' not found")


@router.get("/board")
async def get_board():
    return _board.to_dict()


@router.get("/stackup")
async def get_stackup():
    return stackup_to_dict()


@router.get("/netclasses")
async def get_net_classes():
    return net_classes_to_dict()


@router.get("/design-rules")
async def get_design_rules():
    return {
        "manufacturing": DEFAULT_DESIGN_RULES.to_dict(),
        "isolation": DEFAULT_ISOLATION_RULES.to_dict(),
    }


@router.get("/components")
async def get_components():
    return [comp.to_dict() for comp in _components]


@router.put("/components/{ref}/position")
async def update_component_position(ref: str, update: PositionUpdate):
    comp = _find_component(ref)
    comp.x_mm = update.x_mm
    comp.y_mm = update.y_mm
    comp.rotation_deg = update.rotation_deg
    return comp.to_dict()


@router.post("/components/reset")
async def reset_components():
    global _components
    _components = default_layout()
    return [comp.to_dict() for comp in _components]


@router.get("/ratsnest")
async def get_ratsnest():
    return [line.to_dict() for line in build_ratsnest(_components)]


@router.get("/drc")
async def get_drc():
    return run_drc(
        _components,
        _board,
        isolation_rules=DEFAULT_ISOLATION_RULES,
        net_classes=DEFAULT_NET_CLASSES,
    )
