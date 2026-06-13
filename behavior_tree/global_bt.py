from __future__ import annotations

import asyncio
import logging

from behavior_tree.nodes import (
    ActionNode, BTNode, ConditionNode, NodeStatus,
    SequenceNode, SelectorNode,
)
from world_model.model import ObjectState, ObjectType, SharedWorldModel
from world_model.events import EventBus

logger = logging.getLogger(__name__)


class GlobalBehaviorTree:
    def __init__(
        self,
        world_model: SharedWorldModel,
        event_bus: EventBus,
        agents: dict,
    ) -> None:
        self._world_model = world_model
        self._event_bus = event_bus
        self._agents = agents
        self._root = self._build_tree()

    def _build_tree(self) -> BTNode:
        async def scout_search(ctx: dict) -> NodeStatus:
            scout = self._agents.get("scout")
            if scout:
                await scout.run_cycle()
            return NodeStatus.SUCCESS

        async def is_qr_found(ctx: dict) -> bool:
            results = await self._world_model.query(
                object_type=ObjectType.QR_CODE, state=ObjectState.FOUND
            )
            return len(results) > 0

        async def dispatch_transport(ctx: dict) -> NodeStatus:
            transport = self._agents.get("transport")
            if transport:
                await transport.run_cycle()
                return NodeStatus.SUCCESS
            return NodeStatus.FAILURE

        async def is_transport_arrived(ctx: dict) -> bool:
            results = await self._world_model.query(state=ObjectState.REACHED)
            return len(results) > 0

        async def dispatch_manipulator(ctx: dict) -> NodeStatus:
            manipulator = self._agents.get("manipulator")
            if manipulator:
                await manipulator.run_cycle()
                return NodeStatus.SUCCESS
            return NodeStatus.FAILURE

        async def continue_search(ctx: dict) -> NodeStatus:
            logger.info("BT: continuing search, no QR found yet")
            return NodeStatus.SUCCESS

        pickup_path = SequenceNode([
            ConditionNode(is_transport_arrived),
            ActionNode(dispatch_manipulator),
        ])

        qr_found_path = SequenceNode([
            ConditionNode(is_qr_found),
            ActionNode(dispatch_transport),
            pickup_path,
        ])

        qr_handling = SelectorNode([
            qr_found_path,
            ActionNode(continue_search),
        ])

        mission_root = SequenceNode([
            ActionNode(scout_search),
            qr_handling,
        ])

        return mission_root

    async def tick(self) -> NodeStatus:
        context: dict = {}
        return await self._root.tick(context)

    async def run(self, interval: float = 1.0) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(interval)
