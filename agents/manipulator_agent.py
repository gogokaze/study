from __future__ import annotations

import logging

from agents.base_agent import AgentRole, BaseAgent
from world_model.events import EventType
from world_model.model import ObjectState, ObjectType

logger = logging.getLogger(__name__)


class ManipulatorAgent(BaseAgent):
    def __init__(self, agent_id, world_model, event_bus) -> None:
        super().__init__(agent_id, AgentRole.MANIPULATOR, world_model, event_bus)
        self._telemetry = {}
        self._target_id: str | None = None

    async def perceive(self) -> None:
        if self._device is not None:
            try:
                packet = self._device.simulate()
                self._telemetry = {"battery": packet.battery, **(packet.extra or {})}
            except Exception:
                self._telemetry = {}

    async def decide(self) -> str:
        reached_objs = await self._world_model.query(state=ObjectState.REACHED)
        transport_assigned = [
            o for o in reached_objs
            if o.assigned_to is not None and o.object_type == ObjectType.QR_CODE
        ]
        if transport_assigned:
            self._target_id = transport_assigned[0].id
            return "PICK_PLACE"
        return "IDLE"

    async def act(self, action: str, params: dict) -> None:
        if action == "PICK_PLACE" and self._target_id:
            await self._world_model.update_state(self._target_id, ObjectState.COMPLETED)
            await self.publish_event(
                EventType.TASK_COMPLETE,
                {"action": action, "target": self._target_id},
                world_object_id=self._target_id,
            )
            self._target_id = None
        else:
            logger.info("Manipulator %s action: %s", self.agent_id, action)
