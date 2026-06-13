from __future__ import annotations

import asyncio

from agents.base_agent import BaseAgent


class LocalBehaviorTree:
    def __init__(self, agent: BaseAgent) -> None:
        self._agent = agent

    async def tick(self) -> None:
        await self._agent.run_cycle()

    async def run(self, interval: float = 0.5) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(interval)
