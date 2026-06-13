from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional


class ObjectType(Enum):
    QR_CODE = "qr_code"
    ROBOT = "robot"
    TARGET = "target"
    OBSTACLE = "obstacle"
    ZONE = "zone"
    ITEM = "item"


class ObjectState(Enum):
    UNKNOWN = "unknown"
    FOUND = "found"
    ACTIVE = "active"
    REACHED = "reached"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorldObject:
    id: str
    object_type: ObjectType
    state: ObjectState
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    confidence: float = 1.0
    discovered_by: str = ""
    assigned_to: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SharedWorldModel:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._objects: dict[str, WorldObject] = {}
        self._callbacks: list[Callable[[WorldObject], None]] = []

    async def upsert(self, obj: WorldObject) -> None:
        async with self._lock:
            obj.updated_at = datetime.now(timezone.utc)
            if obj.id not in self._objects:
                obj.created_at = obj.updated_at
            self._objects[obj.id] = obj
        for cb in self._callbacks:
            try:
                result = cb(obj)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

    async def get(self, object_id: str) -> Optional[WorldObject]:
        async with self._lock:
            return self._objects.get(object_id)

    async def query(
        self,
        object_type: Optional[ObjectType] = None,
        state: Optional[ObjectState] = None,
        assigned_to: Optional[str] = None,
    ) -> list[WorldObject]:
        async with self._lock:
            results = list(self._objects.values())
        if object_type is not None:
            results = [o for o in results if o.object_type == object_type]
        if state is not None:
            results = [o for o in results if o.state == state]
        if assigned_to is not None:
            results = [o for o in results if o.assigned_to == assigned_to]
        return results

    async def assign(self, object_id: str, agent_id: str) -> bool:
        async with self._lock:
            obj = self._objects.get(object_id)
            if obj is None:
                return False
            obj.assigned_to = agent_id
            obj.updated_at = datetime.now(timezone.utc)
            return True

    async def update_state(self, object_id: str, new_state: ObjectState) -> bool:
        async with self._lock:
            obj = self._objects.get(object_id)
            if obj is None:
                return False
            obj.state = new_state
            obj.updated_at = datetime.now(timezone.utc)
            return True

    def subscribe(self, callback: Callable[[WorldObject], None]) -> None:
        self._callbacks.append(callback)

    async def snapshot(self) -> dict:
        async with self._lock:
            return {
                oid: {
                    "id": o.id,
                    "object_type": o.object_type.value,
                    "state": o.state.value,
                    "position": {"x": o.x, "y": o.y, "z": o.z},
                    "confidence": o.confidence,
                    "discovered_by": o.discovered_by,
                    "assigned_to": o.assigned_to,
                    "metadata": o.metadata,
                    "created_at": o.created_at.isoformat(),
                    "updated_at": o.updated_at.isoformat(),
                }
                for oid, o in self._objects.items()
            }
