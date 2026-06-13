from __future__ import annotations

import logging
import uuid

from agents.base_agent import AgentRole, BaseAgent
from world_model.events import EventType
from world_model.model import ObjectState, ObjectType, WorldObject

logger = logging.getLogger(__name__)


class TransportAgent(BaseAgent):
    def __init__(self, agent_id, world_model, event_bus) -> None:
        super().__init__(agent_id, AgentRole.TRANSPORT, world_model, event_bus)
        self._telemetry = {}
        self._target_id: str | None = None

    async def perceive(self) -> None:
        if self._device is not None:
            try:
                packet = self._device.simulate()
                self._telemetry = {"battery": packet.battery, **(packet.extra or {})}
            except Exception:
                self._telemetry = {}
        robot_obj = WorldObject(
            id=f"robot-{self.agent_id}",
            object_type=ObjectType.ROBOT,
            state=ObjectState.ACTIVE,
            x=self._telemetry.get("x", 0.0),
            y=self._telemetry.get("y", 0.0),
            z=0.0,
            discovered_by=self.agent_id,
            assigned_to=self.agent_id,
        )
        await self._world_model.upsert(robot_obj)

    async def decide(self) -> str:
        found_qrs = await self._world_model.query(
            object_type=ObjectType.QR_CODE, state=ObjectState.FOUND
        )
        unassigned = [o for o in found_qrs if o.assigned_to is None]
        if unassigned:
            target = unassigned[0]
            await self._world_model.assign(target.id, self.agent_id)
            self._target_id = target.id
            return "NAVIGATE"
        return "PATROL"

    async def act(self, action: str, params: dict) -> None:
        if action == "NAVIGATE" and self._target_id:
            await self._world_model.update_state(self._target_id, ObjectState.REACHED)
            await self.publish_event(
                EventType.TASK_COMPLETE,
                {"action": action, "target": self._target_id},
                world_object_id=self._target_id,
            )
            self._target_id = None
        else:
            logger.info("Transport %s action: %s", self.agent_id, action)
