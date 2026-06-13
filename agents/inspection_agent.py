from __future__ import annotations

import logging

from agents.base_agent import AgentRole, BaseAgent
from world_model.events import EventSeverity, EventType

logger = logging.getLogger(__name__)


class InspectionAgent(BaseAgent):
    def __init__(self, agent_id, world_model, event_bus) -> None:
        super().__init__(agent_id, AgentRole.INSPECTION, world_model, event_bus)
        self._telemetry = {}
        self._warning = False

    async def perceive(self) -> None:
        if self._device is not None:
            try:
                packet = self._device.simulate()
                self._telemetry = {"battery": packet.battery, **(packet.extra or {})}
            except Exception:
                self._telemetry = {}
        vibration = self._telemetry.get("vibration", 0.0)
        spindle_temp = self._telemetry.get("spindle_temp", 0.0)
        if (vibration or 0.0) > 0.12 or (spindle_temp or 0.0) > 55:
            self._warning = True
            await self.publish_event(
                EventType.TOOL_WEAR_WARNING,
                {"vibration": vibration, "spindle_temp": spindle_temp},
                severity=EventSeverity.WARNING,
            )
        else:
            self._warning = False

    async def decide(self) -> str:
        return "ALERT" if self._warning else "MONITOR"

    async def act(self, action: str, params: dict) -> None:
        if action == "ALERT":
            logger.warning("Inspection %s: tool wear alert!", self.agent_id)
        else:
            logger.info("Inspection %s: monitoring nominal", self.agent_id)
