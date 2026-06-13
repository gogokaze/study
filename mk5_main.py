from __future__ import annotations

import asyncio
import logging

from world_model.model import SharedWorldModel
from world_model.events import EventBus
from agents.scout_agent import ScoutAgent
from agents.transport_agent import TransportAgent
from agents.manipulator_agent import ManipulatorAgent
from agents.inspection_agent import InspectionAgent
from agents.submarine_agent import SubmarineAgent
from behavior_tree.global_bt import GlobalBehaviorTree
from behavior_tree.local_bt import LocalBehaviorTree

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    world_model = SharedWorldModel()
    event_bus = EventBus()

    scout = ScoutAgent("scout-01", world_model, event_bus)
    transport = TransportAgent("transport-01", world_model, event_bus)
    manipulator = ManipulatorAgent("manipulator-01", world_model, event_bus)
    inspection = InspectionAgent("inspection-01", world_model, event_bus)
    submarine = SubmarineAgent("submarine-01", world_model, event_bus)

    try:
        from devices.gt3_drone import GT3Drone
        from devices.robot_arm import RobotArm
        from devices.cnc_machine import CNCMachine
        from devices.submarine import LegoSubmarine

        scout.bind_device(GT3Drone("GT3-scout"))
        transport.bind_device(GT3Drone("GT3-transport"))
        manipulator.bind_device(RobotArm("ARM-01"))
        inspection.bind_device(CNCMachine("CNC-01"))
        submarine.bind_device(LegoSubmarine("SUB-01"))
        logger.info("Devices bound successfully")
    except Exception as exc:
        logger.warning("Could not bind devices: %s", exc)

    agents = {
        "scout": scout,
        "transport": transport,
        "manipulator": manipulator,
        "inspection": inspection,
        "submarine": submarine,
    }

    gbt = GlobalBehaviorTree(world_model, event_bus, agents)
    local_bts = [LocalBehaviorTree(a) for a in [inspection, submarine]]

    tick_count = 0

    async def run_ticks(coro_factory, n: int) -> None:
        for _ in range(n):
            await coro_factory()

    await asyncio.gather(
        run_ticks(gbt.tick, 10),
        run_ticks(local_bts[0].tick, 10),
        run_ticks(local_bts[1].tick, 10),
    )

    snapshot = await world_model.snapshot()
    print("\n=== World Model Snapshot ===")
    import json
    print(json.dumps(snapshot, indent=2))
    print(f"\nTotal objects: {len(snapshot)}")
    print(f"Events in history: {len(event_bus.get_history())}")


if __name__ == "__main__":
    asyncio.run(main())
