from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from world_model.model import SharedWorldModel
from world_model.events import EventBus

router = APIRouter(prefix="/api/mk5")

_world_model: Optional[SharedWorldModel] = None
_event_bus: Optional[EventBus] = None
_agents: dict = {}


def init(world_model: SharedWorldModel, event_bus: EventBus, agents: dict) -> None:
    global _world_model, _event_bus, _agents
    _world_model = world_model
    _event_bus = event_bus
    _agents = agents


@router.get("/world")
async def get_world():
    if _world_model is None:
        return {}
    return await _world_model.snapshot()


@router.get("/events")
async def get_events(event_type: Optional[str] = None, limit: int = 50):
    if _event_bus is None:
        return []
    history = _event_bus.get_history(event_type=event_type, limit=limit)
    return [
        {
            "event_id": e.event_id,
            "event_type": e.event_type,
            "agent_id": e.agent_id,
            "severity": e.severity.value,
            "timestamp": e.timestamp.isoformat(),
            "payload": e.payload,
            "world_object_id": e.world_object_id,
        }
        for e in history
    ]


@router.get("/agents")
async def get_agents():
    return {
        agent_id: {
            "agent_id": agent.agent_id,
            "role": agent.role.value,
            "status": agent.status.value,
        }
        for agent_id, agent in _agents.items()
    }
