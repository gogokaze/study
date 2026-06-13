"""Robot arm pick-and-place mission."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Pose:
    x: float = 0.0    # mm
    y: float = 0.0
    z: float = 300.0
    rx: float = 0.0   # degrees
    ry: float = 0.0
    rz: float = 0.0

    def __str__(self) -> str:
        return (
            f"Pose(x={self.x:.1f}, y={self.y:.1f}, z={self.z:.1f}, "
            f"rx={self.rx:.1f}, ry={self.ry:.1f}, rz={self.rz:.1f})"
        )


@dataclass
class ArmPickPlaceMission:
    """
    Moves the robot arm from *pick_pose* to *place_pose*.

    Sequence:
        1. Move to approach pose above pick point
        2. Descend to pick_pose, close gripper
        3. Ascend, move to approach pose above place point
        4. Descend to place_pose, open gripper
        5. Return to home pose
    """

    pick_pose: Pose
    place_pose: Pose
    approach_offset_z: float = 50.0   # mm above pick/place for approach
    gripper_close_delay: float = 0.3   # seconds to wait for gripper to close
    move_delay: float = 0.4            # simulated motion segment time (s)

    async def execute(self, arm: Any) -> dict:
        """Execute pick-and-place on *arm* device instance."""
        device_id: str = getattr(arm, "device_id", "unknown")
        logger.info(
            "[%s] ArmPickPlaceMission: pick=%s place=%s",
            device_id, self.pick_pose, self.place_pose,
        )

        steps: list[str] = []

        # 1. Approach above pick
        approach_pick = Pose(
            x=self.pick_pose.x,
            y=self.pick_pose.y,
            z=self.pick_pose.z + self.approach_offset_z,
            rx=self.pick_pose.rx,
            ry=self.pick_pose.ry,
            rz=self.pick_pose.rz,
        )
        logger.info("[%s] Step 1 — approach pick: %s", device_id, approach_pick)
        await asyncio.sleep(self.move_delay)
        arm.simulate()
        steps.append(f"approach_pick: {approach_pick}")

        # 2. Descend to pick
        logger.info("[%s] Step 2 — descend to pick: %s", device_id, self.pick_pose)
        await asyncio.sleep(self.move_delay)
        arm.simulate()
        steps.append(f"at_pick: {self.pick_pose}")

        # 3. Close gripper
        logger.info("[%s] Step 3 — closing gripper", device_id)
        await asyncio.sleep(self.gripper_close_delay)
        steps.append("gripper: CLOSED")

        # 4. Ascend from pick
        logger.info("[%s] Step 4 — ascend from pick", device_id)
        await asyncio.sleep(self.move_delay)
        arm.simulate()
        steps.append(f"retract_pick: {approach_pick}")

        # 5. Approach above place
        approach_place = Pose(
            x=self.place_pose.x,
            y=self.place_pose.y,
            z=self.place_pose.z + self.approach_offset_z,
            rx=self.place_pose.rx,
            ry=self.place_pose.ry,
            rz=self.place_pose.rz,
        )
        logger.info("[%s] Step 5 — approach place: %s", device_id, approach_place)
        await asyncio.sleep(self.move_delay)
        arm.simulate()
        steps.append(f"approach_place: {approach_place}")

        # 6. Descend to place
        logger.info("[%s] Step 6 — descend to place: %s", device_id, self.place_pose)
        await asyncio.sleep(self.move_delay)
        arm.simulate()
        steps.append(f"at_place: {self.place_pose}")

        # 7. Open gripper
        logger.info("[%s] Step 7 — opening gripper", device_id)
        await asyncio.sleep(self.gripper_close_delay)
        steps.append("gripper: OPEN")

        # 8. Return home
        home = Pose(x=0.0, y=0.0, z=300.0)
        logger.info("[%s] Step 8 — return home: %s", device_id, home)
        await asyncio.sleep(self.move_delay)
        arm.simulate()
        steps.append("home")

        logger.info("[%s] ArmPickPlaceMission complete", device_id)
        return {
            "mission": "arm_pick_place",
            "device_id": device_id,
            "pick_pose": str(self.pick_pose),
            "place_pose": str(self.place_pose),
            "steps_completed": len(steps),
            "steps": steps,
        }
