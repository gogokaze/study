from __future__ import annotations

import logging

from agents.base_agent import AgentRole, BaseAgent
from world_model.events import EventSeverity, EventType

logger = logging.getLogger(__name__)


class SubmarineAgent(BaseAgent):
    def __init__(self, agent_id, world_model, event_bus) -> None:
        super().__init__(agent_id, AgentRole.SUBMARINE, world_model, event_bus)
        self._telemetry = {}
        self._leak = False

    async def perceive(self) -> None:
        if self._device is not None:
            try:
                packet = self._device.simulate()
                self._telemetry = {"battery": packet.battery, **(packet.extra or {})}
            except Exception:
                self._telemetry = {}
        leak = self._telemetry.get("leak_detected", False)
        self._leak = bool(leak)
        if self._leak:
            await self.publish_event(
                EventType.LEAK_DETECTED,
                {"depth": self._telemetry.get("depth", 0.0)},
                severity=EventSeverity.CRITICAL,
            )

    async def decide(self) -> str:
        if self._leak:
            return "EMERGENCY_SURFACE"
        depth = self._telemetry.get("depth", 0.0) or 0.0
        if depth > 2.0:
            return "DEPTH_HOLD"
        return "EXPLORE"

    async def act(self, action: str, params: dict) -> None:
        if action == "EMERGENCY_SURFACE":
            logger.critical("Submarine %s: EMERGENCY SURFACE!", self.agent_id)
        elif action == "DEPTH_HOLD":
            logger.info("Submarine %s: holding depth", self.agent_id)
        else:
            logger.info("Submarine %s: exploring", self.agent_id)
