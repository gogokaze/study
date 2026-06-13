from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from world_model.model import SharedWorldModel
from world_model.events import EventBus, EventSeverity, EventType, RoboticsEvent

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    SCOUT = "scout"
    TRANSPORT = "transport"
    MANIPULATOR = "manipulator"
    INSPECTION = "inspection"
    SUBMARINE = "submarine"


class AgentStatus(Enum):
    IDLE = "idle"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        world_model: SharedWorldModel,
        event_bus: EventBus,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self._world_model = world_model
        self._event_bus = event_bus
        self._device = None
        self._status = AgentStatus.IDLE

    @property
    def device(self):
        return self._device

    def bind_device(self, device) -> None:
        self._device = device

    @property
    def status(self) -> AgentStatus:
        return self._status

    @abstractmethod
    async def perceive(self) -> None: ...

    @abstractmethod
    async def decide(self) -> str: ...

    @abstractmethod
    async def act(self, action: str, params: dict) -> None: ...

    async def run_cycle(self) -> None:
        self._status = AgentStatus.EXECUTING
        try:
            await self.perceive()
            action = await self.decide()
            await self.act(action, {})
            self._status = AgentStatus.IDLE
        except Exception as exc:
            logger.error("Agent %s cycle error: %s", self.agent_id, exc)
            self._status = AgentStatus.ERROR

    async def publish_event(
        self,
        event_type: str,
        payload: dict,
        severity: EventSeverity = EventSeverity.INFO,
        world_object_id: Optional[str] = None,
    ) -> None:
        event = RoboticsEvent(
            event_type=event_type,
            agent_id=self.agent_id,
            severity=severity,
            payload=payload,
            world_object_id=world_object_id,
        )
        await self._event_bus.publish(event)
