from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable


class NodeStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class BTNode(ABC):
    @abstractmethod
    async def tick(self, context: dict) -> NodeStatus: ...


class SequenceNode(BTNode):
    def __init__(self, children: list[BTNode]) -> None:
        self.children = children

    async def tick(self, context: dict) -> NodeStatus:
        for child in self.children:
            status = await child.tick(context)
            if status != NodeStatus.SUCCESS:
                return status
        return NodeStatus.SUCCESS


class SelectorNode(BTNode):
    def __init__(self, children: list[BTNode]) -> None:
        self.children = children

    async def tick(self, context: dict) -> NodeStatus:
        for child in self.children:
            status = await child.tick(context)
            if status != NodeStatus.FAILURE:
                return status
        return NodeStatus.FAILURE


class ConditionNode(BTNode):
    def __init__(self, condition: Callable[[dict], bool]) -> None:
        self._condition = condition

    async def tick(self, context: dict) -> NodeStatus:
        result = self._condition(context)
        if inspect.isawaitable(result):
            result = await result
        return NodeStatus.SUCCESS if result else NodeStatus.FAILURE


class ActionNode(BTNode):
    def __init__(self, action: Callable[[dict], NodeStatus]) -> None:
        self._action = action

    async def tick(self, context: dict) -> NodeStatus:
        result = self._action(context)
        if inspect.isawaitable(result):
            result = await result
        return result


class InverterNode(BTNode):
    def __init__(self, child: BTNode) -> None:
        self.child = child

    async def tick(self, context: dict) -> NodeStatus:
        status = await self.child.tick(context)
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        if status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
        return status
