from __future__ import annotations

import logging
import random
import uuid

from agents.base_agent import AgentRole, AgentStatus, BaseAgent
from world_model.events import EventSeverity, EventType
from world_model.model import ObjectState, ObjectType, WorldObject

logger = logging.getLogger(__name__)


class ScoutAgent(BaseAgent):
    def __init__(self, agent_id, world_model, event_bus) -> None:
        super().__init__(agent_id, AgentRole.SCOUT, world_model, event_bus)
        self._telemetry = {}
        self._found_qr_id: str | None = None

    async def perceive(self) -> None:
        if self._device is not None:
            try:
                packet = self._device.simulate()
                self._telemetry = {
                    "battery": packet.battery,
                    **(packet.extra or {}),
                }
            except Exception:
                self._telemetry = {}
        battery = self._telemetry.get("battery", 100.0)
        if battery is not None and battery < 20:
            await self.publish_event(
                EventType.BATTERY_LOW,
                {"battery": battery},
                severity=EventSeverity.WARNING,
            )
        if random.random() < 0.02:
            qr_id = f"QR-{uuid.uuid4().hex[:6].upper()}"
            obj = WorldObject(
                id=qr_id,
                object_type=ObjectType.QR_CODE,
                state=ObjectState.FOUND,
                x=random.uniform(0, 10),
                y=random.uniform(0, 10),
                z=0.0,
                discovered_by=self.agent_id,
            )
            await self._world_model.upsert(obj)
            await self.publish_event(
                EventType.QR_FOUND,
                {"qr_id": qr_id},
                world_object_id=qr_id,
            )
            self._found_qr_id = qr_id

    async def decide(self) -> str:
        battery = self._telemetry.get("battery", 100.0)
        if battery is not None and battery < 15:
            return "RTH"
        if self._found_qr_id:
            return "HOVER"
        return "SEARCH"

    async def act(self, action: str, params: dict) -> None:
        logger.info("Scout %s action: %s", self.agent_id, action)
        if action != "HOVER":
            self._found_qr_id = None
